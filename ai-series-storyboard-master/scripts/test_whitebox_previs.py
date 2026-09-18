"""Focused regressions plus an explicit synthetic 24-second render fixture generator."""
import copy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw
import validate_storyboards as sb
import whitebox_previs as wb


EXECUTIONS = [
    'The hooded courier reaches the right hand toward the tube on the table while asking Dialogue [D001]: "Take it." in an even rhythm; the receiver watches the hand before any movement toward the object.',
    'The courier closes the right hand around the tube, then lifts it clear of the table while the other character remains outside contact distance, leaving the object visibly supported by the right hand.',
    'The courier extends the right hand toward the receiver while the tube remains fixed at the grip; after the arm settles, the receiver turns attention to the offered object without taking it yet.',
    'The receiver extends the left hand toward the offered tube as the courier holds the right hand steady; after the approach, both hands meet the grip and establish a brief shared contact.',
    'The courier releases and withdraws the right hand while the receiver takes ownership with the left hand, then draws the tube inward; the contextual Voice-over [D002]: "The exchange is done." occupies the same interval without changing the action.',
    'The receiver retreats with the tube supported by the left hand while the courier remains beside the table; the final On-screen text [D003]: "Later" appears as the separation settles, leaving a clear exit direction and unchanged ownership.',
]


def shot_text(duration=24, count=6):
    scales = ("Wide two-shot of the room and table", "Close view of the courier grip and tube",
              "Medium two-shot of the offered tube", "Medium view favoring the receiver",
              "Close view of the two grips and tube", "Wide two-shot showing the retreat path")
    return "\n\n".join(
        f"Shot {i+1} [{i * duration / count:g}s-{(i+1) * duration / count:g}s]\n"
        f"Shot scale: {scales[i % 6]}.\n"
        "Composition: The relevant pair stays readable around the table.\n"
        "Camera angle: Slightly elevated on the same side of the action axis.\n"
        "Camera movement: Locked camera.\n"
        f"Dramatic execution: {EXECUTIONS[i % 6]}" for i in range(count)
    ) + "\n\nSegment transition: Cut after the receiver clears the table.\nContinuity into next segment: Receiver retains the tube in the left hand."


def fixture(root, prompt_version="2.5"):
    """All sources are synthetic test design, not project canon; never overwrites an existing directory."""
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    art = root / "ART"
    art.mkdir()
    style = root / "STYLE-BASE-v1.0.md"
    style.write_text("## STYLE-BASE-v1.0\n\n~~~text\nVisual ontology: live-action cinema, 16:9. World and period: synthetic test.\n~~~\n", encoding="utf-8")
    script = root / "script.md"
    script.write_text("EP001-SC001 SYNTHETIC TEST ONLY\nTake it.\nThe exchange is done.\nLater\n" + "\n".join(EXECUTIONS), encoding="utf-8")
    definitions = [
        ("CHAR-001", "characters", "主要角色", "Character", "A narrow hooded courier in a flared robe.", ["actor_a", "actor_a_right_grip"]),
        ("CHAR-002", "characters", "主要角色", "Character", "A broad square-capped receiver in a straight coat.", ["actor_b", "actor_b_left_grip"]),
        ("CROWD-001", "crowds", "群众演员", "Crowd", "A single background attendant in a plain tapered robe.", ["crowd"]),
        ("SCN-001", "scenes", "核心场景", "Scene", "A rectangular room with a rear central doorway and one central table.", ["floor", "table"]),
        ("PROP-001", "props", "重要道具", "Prop", "A short upright cylindrical tube with a central grasp point.", ["tube", "tube_grip"]),
    ]
    rows, assets = {}, []
    for asset_id, folder, heading, kind, description, names in definitions:
        directory = art / folder
        directory.mkdir(exist_ok=True)
        entity = directory / f"{asset_id}-v1.0.md"
        ref = directory / f"{asset_id}-REF-v1.0.png"
        # Deliberately schematic code-native test diagrams, not AI-generated production art.
        image = Image.new("RGB", (320, 180), "white")
        draw = ImageDraw.Draw(image)
        if kind in ("Character", "Crowd"):
            draw.ellipse((146, 42, 174, 72), fill="gray")
            if asset_id == "CHAR-002":
                draw.rectangle((138, 30, 182, 46), fill="gray")
                draw.rectangle((138, 76, 182, 142), fill="gray")
            else:
                draw.polygon([(160, 15), (142, 42), (178, 42)], fill="gray") if kind == "Character" else None
                draw.polygon([(148, 76), (172, 76), (187, 142), (133, 142)], fill="gray")
            draw.rectangle((138, 144, 150, 164), fill="gray")
            draw.rectangle((170, 144, 182, 164), fill="gray")
        elif kind == "Scene":
            draw.rectangle((20, 20, 135, 80), fill="gray")
            draw.rectangle((185, 20, 300, 80), fill="gray")
            draw.rectangle((135, 20, 185, 35), fill="gray")
            draw.rectangle((125, 95, 195, 108), fill="gray")
            draw.line((130, 108, 130, 150), fill="gray", width=8)
            draw.line((190, 108, 190, 150), fill="gray", width=8)
        else:
            draw.rectangle((145, 50, 175, 140), fill="gray")
            draw.ellipse((145, 42, 175, 58), fill="gray")
        image.save(ref)
        label = f"@{asset_id}-REF-v1.0"
        entity.write_text(f"## {asset_id}-v1.0｜Synthetic test\n- inherits-style: STYLE-BASE-v1.0\n- reference-label: {label}\n- reference-image: {ref.name}\n\n### {kind} Base\n~~~text\n{description}\n~~~\n", encoding="utf-8")
        rows.setdefault(heading, []).append(f"| {asset_id} | Test | synthetic | TEST | {folder}/{entity.name} | {label} |")
        assets.append({"id": asset_id, "file": str(entity), "sha256": wb.digest(entity), "label": label,
                       "image": str(ref), "image_sha256": wb.digest(ref), "observations": "Synthetic diagram contract: " + description,
                       "retained_features": [description], "objects": names})
    index = art / "ASSET-INDEX-v1.0.md"
    index.write_text("## ASSET-INDEX-v1.0\n- inherits-style: STYLE-BASE-v1.0\n- status: approved\n\n" +
                     "\n\n".join(f"### {heading}\n| Asset ID | Name | Basis | Scope | File | Label |\n|---|---|---|---|---|---|\n" + "\n".join(items) for heading, items in rows.items()) + "\n", encoding="utf-8")
    scene = root / "STORYBOARD/EP001/SC001"
    scene.mkdir(parents=True)
    plan = scene / "EP001-SC001-PLAN-v1.0.md"
    segment = scene / "EP001-SC001-SEG001-v1.0.md"
    common = "- inherits-style: STYLE-BASE-v1.0\n- asset-index-snapshot: ASSET-INDEX-v1.0\n- source: script.md\n- source-scene: EP001-SC001\n- coverage: complete\n- status: approved\n- character-assets: CHAR-001, CHAR-002\n- crowd-assets: CROWD-001\n- scene-asset: SCN-001\n- prop-assets: PROP-001\n"
    common += "- asset-files: " + "; ".join(f"{a[0]}={a[1]}/{a[0]}-v1.0.md" for a in definitions) + "\n"
    common += "- reference-calls: " + ", ".join(a["label"] for a in assets) + "\n"
    plan_fields = ("场戏叙事功能", "核心戏剧目标", "起始状态", "结束状态", "空间任务", "连续性入口", "连续性出口")
    segment_fields = ("片段编号", "片段名称", "核心场景", "登场主要角色", "叙事功能", "戏剧目标", "情绪推进", "关键动作", "关键台词、旁白与屏幕文字", "转场方式", "与前后片段衔接", "参考调用")
    numbered = lambda labels: "\n".join(f"{i}. {label}：synthetic interaction test" for i, label in enumerate(labels, 1))
    plan.write_text(f"## {plan.stem}｜Synthetic test\n{common}- source-heading: EP001-SC001 SYNTHETIC TEST ONLY\n- segment-count: 1\n\n### 场戏设计\n{numbered(plan_fields)}\n\n### Source Text Registry\n~~~text\nD001 | Dialogue | CHAR-001 | Take it.\nD002 | Voice-over | NARRATOR | The exchange is done.\nD003 | On-screen text | SCREEN | Later\n~~~\n\n### Segment Catalog\n| Segment ID | Duration | Function | Task | Characters | Crowds | Scene | Props | Source |\n|---|---|---|---|---|---|---|---|---|\n| EP001-SC001-SEG001 | 24s | exchange | handoff | CHAR-001, CHAR-002 | CROWD-001 | SCN-001 | PROP-001 | D001, D002, D003 |\n", encoding="utf-8")
    bases = "\n".join(f"{a[3]} {a[0]}: {a[4]}" for a in definitions)
    prompt = "[FOUNDATION]\nDuration: 24s\nFrame: 16:9\nReferences: " + ", ".join(a["label"] for a in assets) + f"\n{bases}\n\n[ATMOSPHERE AND IMAGE QUALITY]\nStyle Core: Live-action cinema.\nVisual Baseline: Clear physical staging.\nColor and Tonality: Neutral daylight.\n\n[VISUAL CONTENT]\n" + shot_text()
    segment.write_text(f"## {segment.stem}｜Synthetic test\n{common}- inherits-plan: {plan.stem}\n- duration: 24s\n- source-text-ids: D001, D002, D003\n\n### 片段方案\n{numbered(segment_fields)}\n\n### Seedance {prompt_version} Prompt\n~~~text\n{prompt}\n~~~\n", encoding="utf-8")
    output = scene / "PREVIS"
    output.mkdir()
    spec_path = output / "EP001-SC001-SEG001-WB-v1.0.json"
    builder = spec_path.with_suffix(".py")
    shutil.copy2(Path(__file__).parent / "fixtures/interaction_scene.py", builder)
    source = {key: {"path": str(value), "sha256": wb.digest(value)} for key, value in
              (("segment", segment), ("plan", plan), ("script", script), ("style", style))}
    source["asset_index"] = {"path": str(index)}
    source["visual_sha256"] = wb.text_digest(wb.source_shots(prompt)[0])
    spec = {"schema_version": 1, "source": source, "render": {"width": 320, "height": 180, "fps": 12, "frames": 288},
            "assets": assets, "shots": [], "contacts": [],
            "unverifiable": [{"source_id": f"D00{i}", "reason": "Silent/no text; interval retained, sound/text meaning not verified."} for i in range(1, 4)],
            "builder": {"path": builder.name, "sha256": wb.digest(builder)}}
    for i in range(6):
        first, end = i * 48, (i + 1) * 48
        spec["shots"].append({"id": i+1, "start": first, "end": end, "camera": f"camera_{i+1}",
                              "camera_plan": "Locked same-axis camera; coordinates in build script.", "action_plan": EXECUTIONS[i],
                              "visible_objects": ["actor_a", "actor_b", "tube"],
                              "state_in": f"Interaction phase {i} begins", "state_out": f"Interaction phase {i} completes",
                              "review_frames": [first, first+24, end-1]})
    for frame, hand in ((48, "actor_a_right_grip"), (96, "actor_a_right_grip"), (144, "actor_a_right_grip"),
                        (192, "actor_a_right_grip"), (192, "actor_b_left_grip"), (240, "actor_b_left_grip"), (287, "actor_b_left_grip")):
        spec["contacts"].append({"frame": frame, "object": "tube_grip", "anchor": hand, "max_distance": 0.02,
                                 "meaning": "Synthetic pickup/hold/transfer with explicit hand anchor"})
    wb.dump(spec_path, spec)
    return spec_path


class WhiteboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="whitebox-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = fixture(Path(self.temp.name) / "fixture")
        self.spec = wb.load(self.path)

    def save(self):
        wb.dump(self.path, self.spec)

    def test_valid_full_source_and_asset_binding(self):
        self.assertEqual(wb.validate_spec(self.path)["render"]["frames"], 288)

    def test_legacy_prompt_preserves_full_validation(self):
        legacy = fixture(Path(self.temp.name) / "legacy", prompt_version="2.0")
        self.assertEqual(wb.validate_spec(legacy)["render"]["frames"], 288)

    def test_ambiguous_or_unsupported_prompt_rejected(self):
        segment = Path(self.spec["source"]["segment"]["path"])
        original = segment.read_text(encoding="utf-8")
        for invalid in (
            original + "\n### Seedance 2.0 Prompt\n~~~text\nconflicting draft\n~~~\n",
            original + "\n### Seedance 2.5 Prompt\n~~~text\nsecond draft\n~~~\n",
            original.replace("### Seedance 2.5 Prompt", "### Seedance 9.9 Prompt"),
        ):
            with self.subTest(header=invalid[-100:]):
                segment.write_text(invalid, encoding="utf-8")
                self.spec["source"]["segment"]["sha256"] = wb.digest(segment)
                self.save()
                with self.assertRaisesRegex(ValueError, "expected exactly one Seedance"):
                    wb.validate_spec(self.path)

    def minimal(self):
        self.spec.update(schema_version=2, execution={"backend": "blender-mcp", "tool": "mcp__blender__execute_blender_code"},
                         modeling={"level": "minimal-blocking"}, review={"mode": "normal-speed"})
        for shot in self.spec["shots"]:
            shot["review_frames"] = []
        self.spec["contacts"] = []
        self.save()

    def test_minimal_spec_does_not_require_frame_reviews_or_dense_contacts(self):
        self.minimal()
        self.assertEqual(wb.validate_spec(self.path)["schema_version"], 2)
        self.spec["execution"]["backend"] = "direct-cli"
        self.save()
        with self.assertRaisesRegex(ValueError, "Blender MCP"):
            wb.validate_spec(self.path)

    def test_normal_speed_review_without_frame_inventory(self):
        self.minimal()
        video, blend = self.path.with_suffix(".mp4"), self.path.with_suffix(".blend")
        video.write_bytes(b"test-only")
        blend.write_bytes(b"test-only")
        review = {"spec_sha256": wb.digest(self.path), "video_sha256": wb.digest(video), "blend_sha256": wb.digest(blend),
                  "reviewer": "unit-test-schema-only", "method": "normal-speed-playback", "playback_speed": 1,
                  "watched_range": [0, 288], "checks": {k: True for k in ("identity", "action", "camera", "continuity", "no_text")},
                  "issues": [], "evidence": "Schema test; not a published visual review."}
        wb.check_review(review, self.spec, self.path, video, blend)
        review["method"] = "dense-frames"
        with self.assertRaisesRegex(ValueError, "normal-speed"):
            wb.check_review(review, self.spec, self.path, video, blend)

    def test_mcp_finalize_requires_real_record_and_all_rendered_shots(self):
        self.minimal()
        with self.assertRaisesRegex(ValueError, "receipt required"):
            wb.finalize_mcp(self.path, self.spec, None, "ffmpeg", "ffprobe")
        receipt = self.path.with_name("receipt.json")
        wb.dump(receipt, {"backend": "blender-mcp", "tool": self.spec["execution"]["tool"], "spec_sha256": wb.digest(self.path),
                          "calls": [{"operation": "prepare", "result": {"spec_sha256": wb.digest(self.path)}},
                                    {"operation": "finish", "result": {"spec_sha256": wb.digest(self.path)}}]})
        with self.assertRaisesRegex(ValueError, "all shots"):
            wb.finalize_mcp(self.path, self.spec, receipt, "ffmpeg", "ffprobe")

    def test_duration_boundaries(self):
        for value in (8, 10, 12, 24, 30):
            self.assertEqual(sb.parse_duration(f"{value}s"), value)
        for value in ("0s", "30.001s", "-1s", "nans"):
            with self.assertRaises(ValueError):
                sb.parse_duration(value)

    def test_shot_count_and_timeline(self):
        for count in (1, 2, 4, 5, 6, 12, 13):
            result = sb.Result(self.path, "test")
            sb.validate_shots(result, "[VISUAL CONTENT]\n" + shot_text(24, count), 24)
            self.assertEqual(bool(result.errors), not 6 <= count <= 12, result.errors)
        for interval in ("4.1s-8s", "3.9s-8s"):
            result = sb.Result(self.path, "test")
            sb.validate_shots(result, "[VISUAL CONTENT]\n" + shot_text().replace("4s-8s", interval), 24)
            self.assertTrue(result.errors)

    def test_missing_pending_corrupt_and_wrong_version_images(self):
        for fault in ("pending", "missing", "corrupt", "version"):
            with self.subTest(fault=fault):
                spec_path = fixture(Path(self.temp.name) / fault)
                spec = wb.load(spec_path)
                asset = spec["assets"][0]
                entity, image = Path(asset["file"]), Path(asset["image"])
                if fault == "pending":
                    entity.write_text(entity.read_text(encoding="utf-8").replace(image.name, "pending"), encoding="utf-8")
                    asset["sha256"] = wb.digest(entity)
                elif fault == "missing":
                    image.unlink()
                elif fault == "corrupt":
                    image.write_bytes(b"not an image")
                    asset["image_sha256"] = wb.digest(image)
                else:
                    new = image.with_name(image.name.replace("v1.0", "v2.0"))
                    image.rename(new)
                    entity.write_text(entity.read_text(encoding="utf-8").replace(image.name, new.name), encoding="utf-8")
                    asset.update(image=str(new), sha256=wb.digest(entity))
                wb.dump(spec_path, spec)
                with self.assertRaises((ValueError, OSError)):
                    wb.validate_spec(spec_path)

    def test_source_changes_invalidate(self):
        source = Path(self.spec["source"]["segment"]["path"])
        source.write_text(source.read_text(encoding="utf-8").replace("Locked camera", "Slow pan"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "stale content"):
            wb.validate_spec(self.path)

    def test_missing_asset_and_wrong_shot_binding(self):
        for kind in ("asset", "shot", "text"):
            changed = copy.deepcopy(self.spec)
            if kind == "asset":
                changed["assets"].pop()
            elif kind == "shot":
                changed["shots"][1]["start"] += 1
            else:
                changed["unverifiable"].pop()
            wb.dump(self.path, changed)
            with self.assertRaises(ValueError):
                wb.validate_spec(self.path)

    def test_previs_markdown_not_collected(self):
        self.path.with_suffix(".md").write_text("not a formal segment", encoding="utf-8")
        paths = sb.collect_paths([str(self.path.parents[1])])
        self.assertEqual(len(paths), 2)
        self.assertTrue(all("-WB-" not in p.name for p in paths))

    def test_unrelated_index_change_not_invalidating(self):
        index = Path(self.spec["source"]["asset_index"]["path"])
        index.write_text(index.read_text(encoding="utf-8") + "\n### Notes\nUnrelated index notes changed.\n", encoding="utf-8")
        wb.validate_spec(self.path)

    def test_no_video_or_no_review_is_not_complete(self):
        with self.assertRaisesRegex(ValueError, "missing video"):
            wb.check_media(self.path.with_suffix(".mp4"), self.spec)
        video, blend = self.path.with_suffix(".mp4"), self.path.with_suffix(".blend")
        video.write_bytes(b"test-only")
        blend.write_bytes(b"test-only")
        review = {"spec_sha256": wb.digest(self.path), "video_sha256": wb.digest(video), "blend_sha256": wb.digest(blend), "reviewer": "test", "shots": []}
        with self.assertRaisesRegex(ValueError, "incomplete visual review"):
            wb.check_review(review, self.spec, self.path, video, blend)

    def test_visual_failure_and_stale_review_rejected(self):
        video, blend = self.path.with_suffix(".mp4"), self.path.with_suffix(".blend")
        video.write_bytes(b"test-only")
        blend.write_bytes(b"test-only")
        review = {"spec_sha256": wb.digest(self.path), "video_sha256": wb.digest(video), "blend_sha256": wb.digest(blend), "reviewer": "unit-test-only", "shots": []}
        for shot in self.spec["shots"]:
            review["shots"].append({"id": shot["id"], "inspected_frames": shot["review_frames"],
                                    "motion_range": [shot["start"], shot["end"]], "identity": True,
                                    "action": True, "camera": True, "continuity": True, "no_text": True,
                                    "evidence": "Synthetic review schema test only, never published as a review."})
        wb.check_review(review, self.spec, self.path, video, blend)
        review["shots"][0]["action"] = False
        with self.assertRaisesRegex(ValueError, "visual review failed"):
            wb.check_review(review, self.spec, self.path, video, blend)
        review["shots"][0]["action"] = True
        video.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "stale visual review media"):
            wb.check_review(review, self.spec, self.path, video, blend)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg unavailable")
    def test_real_media_rejects_audio_and_frame_mismatch(self):
        video = self.path.with_suffix(".mp4")
        spec = copy.deepcopy(self.spec)
        spec["render"] = {"width": 320, "height": 180, "fps": 12, "frames": 12}
        command = ["ffmpeg", "-v", "error", "-n", "-f", "lavfi", "-i", "color=c=gray:s=320x180:r=12:d=1"]
        subprocess.run(command + ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True)
        wb.check_media(video, spec)
        spec["render"]["frames"] += 1
        with self.assertRaisesRegex(ValueError, "frame count mismatch"):
            wb.check_media(video, spec)
        audio_video = video.with_name("audio.mp4")
        subprocess.run(command + ["-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-c:v", "libx264", "-c:a", "aac", str(audio_video)], check=True)
        with self.assertRaisesRegex(ValueError, "no audio/subtitles"):
            wb.check_media(audio_video, spec)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--make-fixture":
        output = fixture(sys.argv[2])
        wb.validate_spec(output)
        print(output)
    else:
        unittest.main()
