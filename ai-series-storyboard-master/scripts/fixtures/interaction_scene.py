"""SYNTHETIC TEST ONLY: six-shot, 24-second pickup/handoff/release, not production art."""
import math
import bpy
from mathutils import Vector


def build(spec, base_dir):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.background_type = "WORLD"
    scene.world.color = (0.15, 0.15, 0.15)

    def piece(name, location, scale, shape="cube", gray=0.65):
        if shape == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
        elif shape == "cone":
            bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=1, radius2=0.25, depth=2)
        elif shape == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1, depth=2)
        else:
            bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.object
        obj.name, obj.location, obj.scale = name, location, scale
        mat = bpy.data.materials.new(name + "_gray")
        mat.diffuse_color = (gray, gray, gray, 1)
        obj.data.materials.append(mat)
        return obj

    def root(name, location):
        obj = bpy.data.objects.new(name, None)
        scene.collection.objects.link(obj)
        obj.location = location
        return obj

    floor = piece("floor", (0, 0, -0.1), (4, 3, 0.1), gray=0.42)
    piece("rear_wall_left", (-2.4, 2, 1.4), (1.5, 0.12, 1.4), gray=0.52)
    piece("rear_wall_right", (2.4, 2, 1.4), (1.5, 0.12, 1.4), gray=0.52)
    piece("lintel", (0, 2, 2.6), (0.9, 0.12, 0.2), gray=0.52)
    piece("table", (0, 0.15, 0.8), (0.55, 0.4, 0.08), gray=0.55)
    for x in (-0.42, 0.42):
        for y in (-0.15, 0.45):
            piece(f"leg_{x}_{y}", (x, y, 0.36), (0.05, 0.05, 0.36))
    actors = []
    feet = {}
    for name, x, hood in (("actor_a", -1.1, True), ("actor_b", 1.1, False)):
        actor = root(name, (x, 0, 0))
        for suffix, loc, size, shape in (
            ("body", (0, 0, 0.87), (0.3, 0.2, 0.55), "cone" if hood else "cube"),
            ("head", (0, 0, 1.67), (0.18, 0.17, 0.22), "sphere"),
            ("hat", (0, 0, 1.91), (0.23, 0.2, 0.22 if hood else 0.08), "cone" if hood else "cube"),
            ("left_foot", (-0.16, -0.1, 0.16), (0.09, 0.16, 0.16), "cube"),
            ("right_foot", (0.16, -0.1, 0.16), (0.09, 0.16, 0.16), "cube"),
        ):
            part = piece(name + "_" + suffix, loc, size, shape)
            part.parent = actor
            if suffix.endswith("foot"):
                feet[name + "_" + suffix] = part
        actors.append(actor)
    a, b = actors
    right = piece("actor_a_right_grip", (-0.76, -0.3, 1), (0.085, 0.085, 0.085), "sphere")
    left = piece("actor_b_left_grip", (0.76, -0.3, 1), (0.085, 0.085, 0.085), "sphere")
    arm_a = piece("arm_a", (0, 0, 0), (0.07, 0.07, 0.3), "cylinder")
    arm_b = piece("arm_b", (0, 0, 0), (0.07, 0.07, 0.3), "cylinder")
    prop = piece("tube", (0, 0.1, 1), (0.08, 0.08, 0.2), "cylinder", 0.8)
    grip = root("tube_grip", (0, 0, 0))
    grip.parent = prop
    # Cylinder's grasp origin is its center, explicitly used as the hand contact anchor.
    piece("crowd", (0, 1.7, 0.8), (0.2, 0.15, 0.8), "cone", 0.55)
    piece("crowd_head", (0, 1.7, 1.75), (0.15, 0.15, 0.18), "sphere", 0.55)

    def mix(start, end, amount):
        return Vector(start).lerp(Vector(end), max(0, min(1, amount)))

    rest_a, rest_b, table, raised, exchange = (-0.76, -0.3, 1), (0.76, -0.3, 1), (0, 0.1, 1.08), (-0.55, -0.2, 1.3), (0, -0.35, 1.25)
    for frame in range(spec["render"]["frames"]):
        time = frame / spec["render"]["fps"]
        if time < 4:
            right.location = mix(rest_a, table, time / 4)
            left.location, prop.location = rest_b, table
        elif time < 8:
            right.location = mix(table, raised, (time - 4) / 4)
            left.location, prop.location = rest_b, right.location
        elif time < 12:
            right.location = mix(raised, exchange, (time - 8) / 4)
            left.location, prop.location = rest_b, right.location
        elif time < 16:
            right.location = exchange
            left.location = mix(rest_b, exchange, (time - 12) / 4)
            prop.location = right.location
        elif time < 20:
            right.location = mix(exchange, rest_a, (time - 16) / 4)
            left.location = mix(exchange, rest_b, (time - 16) / 4)
            prop.location = left.location
        else:
            b.location.x = 1.1 + 0.5 * (time - 20) / 4
            left.location = (rest_b[0] + b.location.x - 1.1, rest_b[1], rest_b[2])
            right.location, prop.location = rest_a, left.location
        # Alternating lifted steps: stance foot stays in world space between swings.
        if time >= 20:
            step_time = time - 20
            for side, offset, delay in (("left", -0.16, 0), ("right", 0.16, 1)):
                foot = feet[f"actor_b_{side}_foot"]
                phase = max(0, step_time - delay)
                cycle = int(phase // 2)
                swing = min(1, phase % 2)
                world_x = 1.1 + offset + 0.25 * (cycle + swing)
                foot.location.x = world_x - b.location.x
                foot.location.z = 0.16 + 0.08 * math.sin(math.pi * swing)
                foot.keyframe_insert(data_path="location", frame=frame + 1)
        a.rotation_euler.z = -0.15 * min(1, time / 12)
        b.rotation_euler.z = 0.15 * min(1, max(0, (time - 12) / 4))
        for arm, actor, hand, offset in ((arm_a, a, right, 0.25), (arm_b, b, left, -0.25)):
            shoulder = Vector((actor.location.x + offset, -0.05, 1.3))
            delta = hand.location - shoulder
            arm.location = (shoulder + hand.location) / 2
            arm.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
            arm.scale.z = delta.length / 2
        if time < 20:
            for side in ("left", "right"):
                feet[f"actor_b_{side}_foot"].keyframe_insert(data_path="location", frame=frame + 1)
        for obj in (a, b, right, left, prop, arm_a, arm_b):
            for channel in ("location", "rotation_euler", "scale"):
                obj.keyframe_insert(data_path=channel, frame=frame + 1)
    views = [((4, -7, 3), (0, 0, 1)), ((-2, -3, 2.3), (-0.3, 0, 1.2)),
             ((1, -4, 2), (-0.35, 0, 1.3)), ((-1, -4, 2), (0.4, 0, 1.3)),
             ((0, -3, 2), (0, -0.1, 1.2)), ((-4, -7, 3), (0.3, 0, 1))]
    for shot, (location, target) in zip(spec["shots"], views):
        camera_data = bpy.data.cameras.new(shot["camera"])
        camera = bpy.data.objects.new(shot["camera"], camera_data)
        scene.collection.objects.link(camera)
        camera.location = location
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera_data.lens = 45
