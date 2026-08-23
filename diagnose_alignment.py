import bpy
from mathutils import Vector

print("=" * 80)
print("ALIGNMENT DIAGNOSTIC")
print("=" * 80)

root = bpy.data.objects.get("AlignTest")
if not root:
    print("ERROR: AlignTest root not found")
else:
    target = bpy.data.objects.get("AlignTest_Target")
    if not target:
        print("ERROR: Target not found")
    else:
        # Target bbox
        target_bbox = [target.matrix_world @ Vector(c) for c in target.bound_box]
        tx_coords = [c.x for c in target_bbox]
        ty_coords = [c.y for c in target_bbox]
        tz_coords = [c.z for c in target_bbox]
        print(f"TARGET: X[{min(tx_coords):.6f},{max(tx_coords):.6f}] Y[{min(ty_coords):.6f},{max(ty_coords):.6f}] Z[{min(tz_coords):.6f},{max(tz_coords):.6f}]")

    for child in bpy.data.objects:
        current = child.parent
        is_child = False
        while current:
            if current == root:
                is_child = True
                break
            current = current.parent
        if is_child and child != root:
            if child.bound_box:
                world_corners = [child.matrix_world @ Vector(c) for c in child.bound_box]
                xs = [c.x for c in world_corners]
                ys = [c.y for c in world_corners]
                zs = [c.z for c in world_corners]
                print(f"{child.name}: X[{min(xs):.6f},{max(xs):.6f}] Y[{min(ys):.6f},{max(ys):.6f}] Z[{min(zs):.6f},{max(zs):.6f}]")

print("=" * 80)
print("ALIGNMENT DIAGNOSTIC COMPLETE")
print("=" * 80)