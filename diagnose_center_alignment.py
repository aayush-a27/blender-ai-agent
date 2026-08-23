import bpy
from mathutils import Vector

print("=" * 80)
print("CENTER ALIGNMENT DIAGNOSTIC")
print("=" * 80)

root = bpy.data.objects.get("TransformedParent")
if not root:
    print("ERROR: TransformedParent root not found")
else:
    target = bpy.data.objects.get("Parented_Target")
    source = bpy.data.objects.get("Parented_Source")
    
    if not target:
        print("ERROR: Parented_Target not found")
    else:
        print(f"TARGET: {target.name}")
        target_bbox = [target.matrix_world @ Vector(c) for c in target.bound_box]
        tx_coords = [c.x for c in target_bbox]
        ty_coords = [c.y for c in target_bbox]
        tz_coords = [c.z for c in target_bbox]
        print(f"  WORLD BBOX: X[{min(tx_coords):.6f},{max(tx_coords):.6f}] Y[{min(ty_coords):.6f},{max(ty_coords):.6f}] Z[{min(tz_coords):.6f},{max(tz_coords):.6f}]")
        print(f"  Z center = {(min(tz_coords) + max(tz_coords)) / 2:.6f}")
        print()
    
    if not source:
        print("ERROR: Parented_Source not found")
    else:
        print(f"SOURCE: {source.name}")
        source_bbox = [source.matrix_world @ Vector(c) for c in source.bound_box]
        sx_coords = [c.x for c in source_bbox]
        sy_coords = [c.y for c in source_bbox]
        sz_coords = [c.z for c in source_bbox]
        print(f"  WORLD BBOX: X[{min(sx_coords):.6f},{max(sx_coords):.6f}] Y[{min(sy_coords):.6f},{max(sy_coords):.6f}] Z[{min(sz_coords):.6f},{max(sz_coords):.6f}]")
        print(f"  X center = {(min(sx_coords) + max(sx_coords)) / 2:.6f}")
        print(f"  Z center = {(min(sz_coords) + max(sz_coords)) / 2:.6f}")
        print()
        
        # Calculate alignment errors
        if target and source:
            target_bbox = [target.matrix_world @ Vector(c) for c in target.bound_box]
            source_bbox = [source.matrix_world @ Vector(c) for c in source.bound_box]
            
            tx_coords = [c.x for c in target_bbox]
            tz_coords = [c.z for c in target_bbox]
            sx_coords = [c.x for c in source_bbox]
            sz_coords = [c.z for c in source_bbox]
            
            target_x_min = min(tx_coords)
            target_z_min = min(tz_coords)
            target_z_max = max(tz_coords)
            target_z_center = (target_z_min + target_z_max) / 2
            
            source_x_min = min(sx_coords)
            source_z_min = min(sz_coords)
            source_z_max = max(sz_coords)
            source_z_center = (source_z_min + source_z_max) / 2
            
            # X MIN alignment error
            x_min_error = source_x_min - target_x_min
            print(f"X MIN ALIGNMENT ERROR: {x_min_error:.6f} (source_x_min={source_x_min:.6f}, target_x_min={target_x_min:.6f})")
            
            # Z CENTER alignment error
            z_center_error = source_z_center - target_z_center
            print(f"Z CENTER ALIGNMENT ERROR: {z_center_error:.6f} (source_z_center={source_z_center:.6f}, target_z_center={target_z_center:.6f})")

print("=" * 80)
print("CENTER ALIGNMENT DIAGNOSTIC COMPLETE")
print("=" * 80)