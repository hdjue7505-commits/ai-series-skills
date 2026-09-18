#!/usr/bin/env python3
"""Validate, render and check source-bound whitebox previs. No NLP or automatic visual approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import validate_storyboards as sb


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve(base, value):
    return (base / value).resolve()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_hash(path, expected):
    require(path.is_file(), f"missing file: {path}")
    require(digest(path) == expected, f"stale content: {path}")


def source_shots(prompt):
    require(prompt.count("[VISUAL CONTENT]") == 1, "VISUAL CONTENT must occur once")
    visual = prompt.split("[VISUAL CONTENT]", 1)[1].strip()
    matches = list(re.finditer(r"^Shot (\d+) \[(\d+(?:\.\d+)?)s-(\d+(?:\.\d+)?)s\]$", visual, re.M))
    return visual, matches


def validate_spec(path):
    """Fail closed on structure/provenance; observations are declarations requiring visual QA."""
    from PIL import Image

    path = Path(path).resolve()
    base = path.parent
    spec = load(path)
    require(spec["schema_version"] in (1, 2), "unsupported whitebox schema")
    minimal = spec["schema_version"] == 2
    if minimal:
        require(spec.get("execution", {}).get("backend") == "blender-mcp", "new whitebox requires Blender MCP")
        require(bool(spec["execution"].get("tool")), "actual MCP tool required")
        require(spec.get("modeling", {}).get("level") == "minimal-blocking", "new whitebox must use minimal blocking")
        require(spec.get("review", {}).get("mode") == "normal-speed", "new whitebox requires normal-speed review")
    require(re.fullmatch(rf"EP\d{{3}}-SC\d{{3}}-SEG\d{{3}}-WB-{sb.VERSION}", path.stem), "invalid WB filename")
    source = spec["source"]
    files = {key: resolve(base, source[key]["path"]) for key in ("segment", "plan", "script", "style", "asset_index")}
    for key in ("segment", "plan", "script", "style"):
        check_hash(files[key], source[key]["sha256"])
    style_id, style_raw, traits = sb.validate_style(files["style"])
    _, assets = sb.load_approved_index(files["asset_index"], style_id)
    plan_result, plan = sb.validate_plan(files["plan"], style_id, assets, files["script"], sb.read(files["script"]))
    require(not plan_result.errors and plan is not None, f"invalid plan: {plan_result.errors}")
    result = sb.validate_segment(files["segment"], style_id, style_raw, assets, files["script"], plan, traits)
    require(not result.errors, f"invalid segment: {result.errors}")
    raw = sb.read(files["segment"])
    values = sb.metadata(raw)
    require(values["status"] == "approved", "whitebox requires approved segment")
    segment_id = re.sub(rf"-{sb.VERSION}$", "", files["segment"].stem)
    require(path.stem.split("-WB-")[0] == segment_id, "WB belongs to another segment")
    prompt = sb.fenced_section(raw, "Seedance 2.0 Prompt")
    visual, originals = source_shots(prompt)
    require(text_digest(visual) == source["visual_sha256"], "stale VISUAL CONTENT")
    render = spec["render"]
    fps = render["fps"]
    require(type(fps) is int and 1 <= fps <= 120, "fps must be integer 1..120")
    width, height = render["width"], render["height"]
    require(all(type(v) is int and v > 0 and v % 2 == 0 for v in (width, height)) and width * 9 == height * 16,
            "render dimensions must be positive even 16:9")
    duration = sb.parse_duration(values["duration"])
    frames = round(duration * fps)
    require(frames > 0 and abs(frames / fps - duration) <= 1 / fps, "duration is not frame representable")
    require(type(render["frames"]) is int and render["frames"] == frames, "frame count mismatch")
    bindings = sb.parse_asset_files(values["asset-files"])
    bound = spec["assets"]
    require(len(bound) == len(bindings) and {a["id"] for a in bound} == set(bindings), "asset coverage mismatch")
    all_objects = set()
    for asset in bound:
        asset_id = asset["id"]
        entity = files["asset_index"].parent / assets[asset_id].relative_file
        require(resolve(base, asset["file"]) == entity.resolve(), f"wrong entity file: {asset_id}")
        check_hash(entity, asset["sha256"])
        require(asset["label"] == assets[asset_id].reference_label, f"wrong label: {asset_id}")
        entity_meta = sb.metadata(sb.read(entity))
        registered = entity_meta.get("reference-image", "pending")
        require(registered != "pending", f"reference-image pending: {asset_id}")
        # Honor an explicitly registered project-root convention; never guess candidates.
        declared_root = entity_meta.get("reference-path-root")
        if declared_root:
            project_root = files["asset_index"].parent.parent.resolve()
            if project_root.as_posix() in declared_root.replace("\\", "/"):
                reference = resolve(project_root, registered)
            else:
                root_path = Path(declared_root)
                require(root_path.is_absolute() and root_path.is_dir(), "invalid declared reference-path-root")
                reference = resolve(root_path, registered)
        else:
            reference = resolve(entity.parent, registered)
        require(resolve(base, asset["image"]) == reference, f"unregistered image: {asset_id}")
        version = entity.stem.split(f"{asset_id}-", 1)[1]
        require(re.search(rf"{re.escape(version)}(?:[^\d.]|$)", reference.stem), f"image version mismatch: {asset_id}")
        check_hash(reference, asset["image_sha256"])
        with Image.open(reference) as image:
            image.verify()
        with Image.open(reference) as image:
            image.load()
        require(asset["observations"].strip() and asset["retained_features"], f"missing image observations: {asset_id}")
        names = asset["objects"]
        require(names and len(set(names)) == len(names), f"missing/duplicate model objects: {asset_id}")
        require(not all_objects.intersection(names), "model object bound to multiple assets")
        all_objects.update(names)
    shots = spec["shots"]
    require(len(shots) == len(originals), "shot count differs from VISUAL CONTENT")
    previous = 0
    for shot, original in zip(shots, originals):
        number, start, end = original.groups()
        require(shot["id"] == int(number), "shot ID mismatch")
        first, last = round(float(start) * fps), round(float(end) * fps)
        require(type(shot["start"]) is int and type(shot["end"]) is int
                and shot["start"] == first == previous and shot["end"] == last > first, "shot boundary mismatch")
        require(shot["camera"] and shot["camera_plan"].strip() and shot["action_plan"].strip(), "missing executable shot interpretation")
        require(shot["visible_objects"] and set(shot["visible_objects"]) <= all_objects, "unknown visible model")
        require(shot["state_in"].strip() and shot["state_out"].strip(), "missing continuity state")
        checkpoints = shot.get("review_frames", [])
        require(all(type(f) is int and first <= f < last for f in checkpoints), "invalid optional review frame")
        if not minimal:
            require(first in checkpoints and last - 1 in checkpoints, "legacy review frames must include shot start/end")
        previous = last
    require(previous == frames, "shots do not cover render")
    for event in spec["contacts"]:
        require(type(event["frame"]) is int and 0 <= event["frame"] < frames, "invalid contact frame")
        require(event["object"] in all_objects and event["anchor"] in all_objects, "unknown contact object/anchor")
        require(math.isfinite(event["max_distance"]) and 0 < event["max_distance"] <= 0.1, "contact tolerance must be (0,0.1] meters")
        require(event["meaning"].strip(), "contact event needs hand/ownership/state meaning")
    calls = set(re.findall(r'(?:Dialogue|Voice-over|On-screen text) \[(D\d+)\]:', visual))
    limits = spec["unverifiable"]
    require({item["source_id"] for item in limits} == calls, "silent/text omission registry mismatch")
    require(all(item["reason"].strip() for item in limits), "unverifiable item needs reason")
    builder = resolve(base, spec["builder"]["path"])
    check_hash(builder, spec["builder"]["sha256"])
    return spec


def check_media(video, spec, ffprobe="ffprobe", ffmpeg="ffmpeg"):
    require(Path(video).is_file(), f"missing video: {video}")
    probe = subprocess.run([ffprobe, "-v", "error", "-count_frames", "-show_streams", "-of", "json", str(video)],
                           check=True, capture_output=True, text=True)
    streams = json.loads(probe.stdout)["streams"]
    require(len(streams) == 1 and streams[0]["codec_type"] == "video", "video must have exactly one video stream, no audio/subtitles")
    stream = streams[0]
    render = spec["render"]
    require((int(stream["width"]), int(stream["height"])) == (render["width"], render["height"]), "media dimensions mismatch")
    require(int(stream["nb_read_frames"]) == render["frames"], "decoded frame count mismatch")
    require(abs(float(stream["duration"]) - render["frames"] / render["fps"]) <= 1 / render["fps"], "media duration mismatch")
    numerator, denominator = map(int, stream["avg_frame_rate"].split("/"))
    require(abs(numerator / denominator - render["fps"]) < 1e-6, "media fps mismatch")
    subprocess.run([ffmpeg, "-v", "error", "-xerror", "-i", str(video), "-map", "0:v:0", "-f", "null", "-"],
                   check=True, capture_output=True)
    return {"frames": render["frames"], "fps": render["fps"], "streams": "video-only", "decode": "pass"}


def check_review(review, spec, spec_path, video, blend):
    require(review["spec_sha256"] == digest(spec_path), "stale visual review spec")
    require(review["video_sha256"] == digest(video) and review["blend_sha256"] == digest(blend), "stale visual review media")
    require(review["reviewer"].strip(), "visual reviewer required")
    if spec["schema_version"] == 2:
        require(review.get("method") == "normal-speed-playback", "normal-speed playback required; no dense-frame substitute")
        require(review.get("playback_speed") == 1, "review must use normal speed")
        require(review.get("watched_range") == [0, spec["render"]["frames"]], "full segment playback required")
        for key in ("identity", "action", "camera", "continuity", "no_text"):
            require(review.get("checks", {}).get(key) is True, f"visual review failed: {key}")
        require(review.get("issues") == [], "unresolved visual issues")
        require(bool(review.get("evidence", "").strip()), "actual playback evidence required")
        return
    require(len(review["shots"]) == len(spec["shots"]), "incomplete visual review")
    for check, shot in zip(review["shots"], spec["shots"]):
        require(check["id"] == shot["id"], "review shot ID mismatch")
        require(set(shot["review_frames"]) <= set(check["inspected_frames"]), "missing reviewed key frames")
        require(check["motion_range"] == [shot["start"], shot["end"]], "continuous action review required")
        for key in ("identity", "action", "camera", "continuity", "no_text"):
            require(check[key] is True, f"visual review failed: shot {shot['id']} {key}")
        require(check["evidence"].strip(), "visual evidence required; no automatic approval")


def executable(value):
    found = shutil.which(value)
    require(found is not None, f"missing executable: {value}")
    return found


def finalize_mcp(path, spec, receipt_path, ffmpeg, ffprobe):
    """Encode already MCP-rendered frames. This function never starts Blender."""
    require(spec["schema_version"] == 2, "finalize-mcp requires schema 2")
    require(receipt_path is not None, "actual MCP receipt required")
    receipt = load(receipt_path)
    require(receipt.get("backend") == "blender-mcp" and receipt.get("tool") == spec["execution"]["tool"], "MCP tool receipt mismatch")
    require(receipt.get("spec_sha256") == digest(path), "stale MCP receipt")
    calls = receipt.get("calls", [])
    require(calls and calls[0].get("operation") == "prepare" and calls[-1].get("operation") == "finish", "incomplete MCP execution receipt")
    require(all(c.get("result", {}).get("spec_sha256") == digest(path) for c in calls), "MCP results must bind this spec")
    rendered = {i for c in calls if c.get("operation") == "render_shots" for i in c["result"].get("rendered_shots", [])}
    require(rendered == {s["id"] for s in spec["shots"]}, "MCP did not render all shots")
    base = path.parent
    report_path = base / (path.stem + "-build.json")
    built = load(report_path)
    require(built.get("backend") == "blender-mcp" and built.get("phase") == "finished" and built.get("spec_sha256") == digest(path), "unfinished or stale MCP build")
    blend, video, qa = path.with_suffix(".blend"), path.with_suffix(".mp4"), path.with_name(path.stem + "-QA.json")
    require(blend.is_file() and blend.stat().st_size > 0, "missing MCP-built project")
    require(not video.exists() and not qa.exists(), "output version exists; use a new version")
    frames = base / (path.stem + "-frames")
    require(len(list(frames.glob("frame-*.png"))) == spec["render"]["frames"], "MCP render sequence incomplete")
    report = {"state": "blocked", "backend": "blender-mcp", "spec_sha256": digest(path),
              "mcp_receipt": str(receipt_path), "receipt_sha256": digest(receipt_path), "unverifiable": spec["unverifiable"]}
    try:
        subprocess.run([executable(ffmpeg), "-v", "error", "-n", "-framerate", str(spec["render"]["fps"]),
                        "-start_number", "1", "-i", str(frames / "frame-%04d.png"), "-map", "0:v:0", "-an", "-sn", "-dn",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)], check=True)
        report["media"] = check_media(video, spec, ffprobe, ffmpeg)
        validate_spec(path)
        report.update(state="rendered", video_sha256=digest(video), blend_sha256=digest(blend),
                      build=built, visual_review="pending-normal-speed-playback")
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        dump(qa, report)


def run_render(path, spec, blender, ffmpeg, ffprobe):
    base = path.parent
    blend, video, qa = path.with_suffix(".blend"), path.with_suffix(".mp4"), path.with_name(path.stem + "-QA.json")
    require(not any(p.exists() for p in (blend, video, qa)), "output version exists; use a new WB version")
    # Resolve dependencies before creating outputs. Never interact with a user's open Blender scene.
    blender, ffmpeg, ffprobe = map(executable, (blender, ffmpeg, ffprobe))
    driver = Path(__file__).with_name("build_whitebox.py")
    report = {"state": "blocked", "spec_sha256": digest(path), "unverifiable": spec["unverifiable"]}
    try:
        with tempfile.TemporaryDirectory(prefix="whitebox-", dir=base) as temporary:
            work = Path(temporary)
            with (base / (path.stem + "-render.log")).open("x", encoding="utf-8") as log:
                subprocess.run([blender, "--background", "--factory-startup", "--python-exit-code", "1",
                                "--python", str(driver), "--", str(path), str(work)], check=True, stdout=log, stderr=subprocess.STDOUT)
            built = load(work / "build-report.json")
            require(built["spec_sha256"] == digest(path), "source changed during build")
            actual = sorted(work.glob("frame-*.png"))
            require(len(actual) == spec["render"]["frames"], "rendered frame sequence incomplete")
            subprocess.run([ffmpeg, "-v", "error", "-n", "-framerate", str(spec["render"]["fps"]),
                            "-start_number", "1", "-i", str(work / "frame-%06d.png"), "-map", "0:v:0", "-an", "-sn", "-dn",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(work / "video.mp4")], check=True)
            report["media"] = check_media(work / "video.mp4", spec, ffprobe, ffmpeg)
            validate_spec(path)  # Reject inputs changed during a long render.
            shutil.move(str(work / "scene.blend"), blend)
            shutil.move(str(work / "video.mp4"), video)
            review_dir = base / (path.stem + "-review")
            review_dir.mkdir(exist_ok=False)
            for frame in sorted({f for shot in spec["shots"] for f in shot["review_frames"]}):
                shutil.copy2(work / f"frame-{frame + 1:06d}.png", review_dir / f"{frame:06d}.png")
            report.update(state="rendered", video_sha256=digest(video), blend_sha256=digest(blend),
                          build=built, visual_review="pending")
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        dump(qa, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("validate", "render", "finalize-mcp", "check"))
    parser.add_argument("spec", type=Path)
    parser.add_argument("--blender", default="blender")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--review", type=Path, help="independently authored visual review JSON; required for complete")
    parser.add_argument("--receipt", type=Path, help="actual Blender MCP call results")
    parser.add_argument("--legacy-cli", action="store_true", help="legacy schema 1 only; requires explicit user approval")
    opts = parser.parse_args()
    try:
        path = opts.spec.resolve()
        spec = validate_spec(path)
        if opts.mode == "render":
            require(spec["schema_version"] == 1 and opts.legacy_cli, "direct Blender CLI disabled: use Blender MCP and finalize-mcp")
            run_render(path, spec, opts.blender, opts.ffmpeg, opts.ffprobe)
        elif opts.mode == "finalize-mcp":
            finalize_mcp(path, spec, opts.receipt, opts.ffmpeg, opts.ffprobe)
        elif opts.mode == "check":
            video, blend = path.with_suffix(".mp4"), path.with_suffix(".blend")
            require(blend.is_file() and blend.stat().st_size > 0, "missing Blender project")
            media = check_media(video, spec, opts.ffprobe, opts.ffmpeg)
            qa_path = path.with_name(path.stem + "-QA.json")
            qa = load(qa_path)
            require(qa["spec_sha256"] == digest(path) and qa["video_sha256"] == digest(video)
                    and qa["blend_sha256"] == digest(blend), "stale render QA")
            # A missing/failed/new review cannot leave an earlier complete status behind.
            qa.update(state="rendered", media=media, visual_review="pending")
            dump(qa_path, qa)
            if opts.review:
                review = load(opts.review)
                check_review(review, spec, path, video, blend)
                qa.update(state="complete", visual_review=review)
                dump(qa_path, qa)
            else:
                print("MEDIA PASS; visual review pending; whitebox is NOT complete")
                return 3
        print(f"PASS {opts.mode}: {path}")
        return 0
    except (ValueError, OSError, KeyError, TypeError, ImportError, subprocess.SubprocessError) as error:
        if opts.mode == "check":
            qa_path = opts.spec.with_name(opts.spec.stem + "-QA.json")
            if qa_path.is_file():
                try:
                    qa = load(qa_path)
                    qa.update(state="blocked", error=str(error))
                    dump(qa_path, qa)
                except (ValueError, OSError, TypeError):
                    pass
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
