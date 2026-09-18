"""Blender background-only driver. Scene-specific builder must define build(spec, base_dir)."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

import bpy


def main():
    spec_path, output = map(Path, sys.argv[sys.argv.index("--") + 1:])
    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes)
    builder = (spec_path.parent / spec["builder"]["path"]).resolve()
    if hashlib.sha256(builder.read_bytes()).hexdigest() != spec["builder"]["sha256"]:
        raise ValueError("builder changed after validation")
    # Builder is reviewed local code, never execute code taken from asset metadata or web pages.
    runpy.run_path(str(builder))["build"](spec, spec_path.parent)
    scene = bpy.context.scene
    render = spec["render"]
    scene.render.fps = render["fps"]
    scene.render.fps_base = 1.0
    scene.frame_start, scene.frame_end = 1, render["frames"]
    scene.render.resolution_x, scene.render.resolution_y = render["width"], render["height"]
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_stamp = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    for obj in scene.objects:
        if obj.type in {"FONT", "SPEAKER"}:
            raise ValueError(f"text/audio object is forbidden: {obj.name}")
    for material in bpy.data.materials:
        if material.use_nodes and any(node.type == "TEX_IMAGE" for node in material.node_tree.nodes):
            raise ValueError("no image textures in whitebox; read reference images, do not project sheets")
    names = {name for asset in spec["assets"] for name in asset["objects"]}
    if not names <= set(scene.objects.keys()):
        raise ValueError(f"missing bound models: {names - set(scene.objects.keys())}")
    scene.timeline_markers.clear()
    for shot in spec["shots"]:
        camera = scene.objects.get(shot["camera"])
        if camera is None or camera.type != "CAMERA":
            raise ValueError(f"missing camera: {shot['camera']}")
        marker = scene.timeline_markers.new(f"Shot {shot['id']}", frame=shot["start"] + 1)
        marker.camera = camera
    contacts = []
    for event in spec["contacts"]:
        scene.frame_set(event["frame"] + 1)
        graph = bpy.context.evaluated_depsgraph_get()
        first = scene.objects[event["object"]].evaluated_get(graph).matrix_world.translation
        second = scene.objects[event["anchor"]].evaluated_get(graph).matrix_world.translation
        distance = (first - second).length
        if distance > event["max_distance"]:
            raise ValueError(f"contact failed: {event['meaning']}, distance={distance}")
        contacts.append({"frame": event["frame"], "distance": distance, "meaning": event["meaning"]})
    scene.frame_set(1)
    scene.camera = scene.objects[spec["shots"][0]["camera"]]
    scene.render.filepath = "//renders/frame-"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "scene.blend"))
    # Explicit filenames and camera assignment avoid marker evaluation/version differences.
    for shot in spec["shots"]:
        scene.camera = scene.objects[shot["camera"]]
        for frame in range(shot["start"], shot["end"]):
            scene.frame_set(frame + 1)
            scene.render.filepath = str(output / f"frame-{frame + 1:06d}.png")
            bpy.ops.render.render(write_still=True)
    (output / "build-report.json").write_text(json.dumps({
        "spec_sha256": hashlib.sha256(spec_bytes).hexdigest(),
        "blender_version": bpy.app.version_string, "contacts": contacts,
        "objects": sorted(names), "frames": render["frames"],
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
