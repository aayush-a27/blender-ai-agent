import bpy
from mathutils import Vector

print("=" * 80)
print("CONTACT PLACEMENT DIAGNOSTIC (Z-axis)")
print("=" * 80)

root = bpy.data.objects.get("TransformedParent")
if not root:
    print("ERROR: TransformedParent root not found")
else:
    base = bpy.data.objects.get("Parented_Target")
    if not base:
        print("ERROR: Base not found")
    else:
        base_bbox = [base.matrix_world @ Vector(c) for c in base.bound_box]
        bx_coords = [c.x for c in base_bbox]
        by_coords = [c.y for c in base_bbox]
        bz_coords = [c.z for c in base_bbox]
        print(f"BASE: X[{min(bx_coords):.6f},{max(bx_coords):.6f}] Y[{min(by_coords):.6f},{max(by_coords):.6f}] Z[{min(bz_coords):.6f},{max(bz_coords):.6f}]")

    # For contact_test.json, the source is "Parented_Source" and we expect Z contact
    source = bpy.data.objects.get("Parented_Source")
    if not source:
        print("ERROR: Parented_Source not found")
    else:
        source_bbox = [source.matrix_world @ Vector(c) for c in source.bound_box]
        sz_coords = [c.z for c in source_bbox]
        source_z_min = min(sz_coords)
        source_z_max = max(sz_coords)
        print(f"SOURCE: {source.name}")
        print(f"  Z bounds: [{source_z_min:.6f}, {source_z_max:.6f}]")

        base_bbox = [base.matrix_world @ Vector(c) for c in base.bound_box]
        bz_coords = [c.z for c in base_bbox]
        base_z_max = max(bz_coords)
        print(f"  BASE Z max: {base_z_max:.6f}")

        # Z CONTACT: source bottom (min Z) should equal base top (max Z) + offset
        z_gap = source_z_min - base_z_max
        print(f"Z CONTACT GAP: {z_gap:.6f} (should be ~0.000000)")

print("=" * 80)
print("CONTACT DIAGNOSTIC COMPLETE")
print("=" * 80)