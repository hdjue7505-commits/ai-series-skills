"""Run INSIDE Blender via a real MCP execute tool; no client or subprocess fallback.

The host validates the spec first. This helper isolates an owned scene, builds
only coarse proxies, renders requested shots, and saves just that scene.
"""
import hashlib
import json
from pathlib import Path
import runpy
import bpy


def inputs(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    spec = json.loads(raw)
    if spec.get("schema_version") != 2 or spec.get("execution", {}).get("backend") != "blender-mcp":
        raise ValueError("Validated schema 2 Blender MCP spec required")
    return path, spec, hashlib.sha256(raw).hexdigest()


def owned(path, sha):
    matches = [s for s in bpy.data.scenes if s.get("wb_spec_path") == str(path) and s.get("wb_spec_sha256") == sha]
    if len(matches) != 1:
        raise ValueError("Exactly one prepared MCP scene required; inspect status before retrying")
    return matches[0]


def report(path, scene, phase):
    data = {"backend": "blender-mcp", "phase": phase, "spec_sha256": scene["wb_spec_sha256"],
            "scene": scene.name, "blender_version": bpy.app.version_string,
            "rendered_shots": json.loads(scene.get("wb_rendered_shots", "[]")),
            "object_count": len(scene.objects)}
    (path.parent / (path.stem + "-build.json")).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def prepare(spec_path):
    path, spec, sha = inputs(spec_path)
    if any(s.get("wb_spec_path") == str(path) for s in bpy.data.scenes):
        raise ValueError("Already prepared; inspect status instead of duplicating")
    if path.with_suffix(".blend").exists() or path.with_suffix(".mp4").exists():
        raise ValueError("Output version already exists")
    builder = (path.parent / spec["builder"]["path"]).resolve()
    if hashlib.sha256(builder.read_bytes()).hexdigest() != spec["builder"]["sha256"]:
        raise ValueError("Builder fingerprint mismatch")
    frames = path.parent / (path.stem + "-frames")
    frames.mkdir(exist_ok=True)
    if any(frames.iterdir()):
        raise ValueError("Frame directory is not empty; inspect the prior run")
    prior = bpy.context.window.scene if bpy.context.window else None
    scene = bpy.data.scenes.new(path.stem)
    scene.world = bpy.data.worlds.new(path.stem + "-world")
    scene["wb_spec_path"], scene["wb_spec_sha256"] = str(path), sha
    scene["wb_rendered_shots"] = "[]"
    try:
        if bpy.context.window:
            bpy.context.window.scene = scene
        with bpy.context.temp_override(scene=scene, view_layer=scene.view_layers[0]):
            runpy.run_path(str(builder))["build"](spec, path.parent)
        names = {n for a in spec["assets"] for n in a["objects"]}
        if not names <= set(scene.objects.keys()):
            raise ValueError("Builder did not supply all asset proxy objects")
        if any(o.type in {"FONT", "SPEAKER"} for o in scene.objects):
            raise ValueError("No text/audio objects in silent whitebox")
        scene.render.fps = spec["render"]["fps"]
        scene.render.fps_base = 1
        scene.render.resolution_x = spec["render"]["width"]
        scene.render.resolution_y = spec["render"]["height"]
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.use_stamp = scene.render.use_compositing = scene.render.use_sequencer = False
        scene.render.filepath = str(frames / "frame-")
        scene.timeline_markers.clear()
        for shot in spec["shots"]:
            marker = scene.timeline_markers.new(str(shot["id"]), frame=shot["start"]+1)
            marker.camera = scene.objects[shot["camera"]]
        return report(path, scene, "prepared")
    except Exception:
        report(path, scene, "blocked")
        if prior and bpy.context.window:
            bpy.context.window.scene = prior
        for obj in list(scene.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.scenes.remove(scene)
        raise
    finally:
        if prior and bpy.context.window:
            bpy.context.window.scene = prior


def render_shots(spec_path, shot_ids):
    path, spec, sha = inputs(spec_path)
    scene = owned(path, sha)
    done = set(json.loads(scene["wb_rendered_shots"]))
    requested = set(shot_ids)
    if not requested or not requested <= {s["id"] for s in spec["shots"]} or requested & done:
        raise ValueError("Invalid or already rendered shot batch; inspect status")
    prior = bpy.context.window.scene if bpy.context.window else None
    try:
        if bpy.context.window:
            bpy.context.window.scene = scene
        for shot in spec["shots"]:
            if shot["id"] not in requested:
                continue
            scene.camera = scene.objects[shot["camera"]]
            scene.frame_start, scene.frame_end = shot["start"]+1, shot["end"]
            bpy.ops.render.render(animation=True, scene=scene.name)
            done.add(shot["id"])
            scene["wb_rendered_shots"] = json.dumps(sorted(done))
            report(path, scene, "rendering")
        return report(path, scene, "rendered")
    finally:
        if prior and bpy.context.window:
            bpy.context.window.scene = prior


def status(spec_path):
    path, _, sha = inputs(spec_path)
    return report(path, owned(path, sha), "status")


def discard_failed(spec_path):
    """Remove only this task's unsaved failed scene; never touch output files."""
    path, _, sha = inputs(spec_path)
    scene = owned(path, sha)
    if json.loads(scene["wb_rendered_shots"]):
        raise ValueError("Rendered work exists; inspect before discarding")
    if bpy.context.window and bpy.context.window.scene == scene:
        raise ValueError("Restore the user's scene before discarding")
    data = report(path, scene, "blocked")
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    return data


def finish(spec_path):
    path, spec, sha = inputs(spec_path)
    scene = owned(path, sha)
    if set(json.loads(scene["wb_rendered_shots"])) != {s["id"] for s in spec["shots"]}:
        raise ValueError("Render remaining shots before finish")
    if path.with_suffix(".blend").exists():
        raise ValueError("Never overwrite an existing project")
    scene.frame_start, scene.frame_end = 1, spec["render"]["frames"]
    scene.frame_set(1)
    scene.camera = scene.objects[spec["shots"][0]["camera"]]
    # Save only the task-owned scene, never unrelated user data or active-file state.
    bpy.data.libraries.write(str(path.with_suffix(".blend")), {scene}, fake_user=True)
    data = report(path, scene, "finished")
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    return data
