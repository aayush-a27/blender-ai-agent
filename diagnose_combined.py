import bpy
from mathutils import Vector

print("=" * 80)
print("TRANSFORMED PARENT COMBINED TEST DIAGNOSTIC")
print("=" * 80)

root = bpy.data.objects.get("TransformedParent")
if not root:
    print("ERROR: TransformedParent root not found")
else:
    print(f"ROOT: {root.name}")
    print(f"  location: {root.location}")
    print(f"  rotation: {root.rotation_euler}")
    print(f"  scale: {root.scale}")
    print(f"  matrix_world: {root.matrix_world}")
    print()

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
        print()
        
        # Calculate alignment/contact errors
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
            
            source_x_min = min(sx_coords)
            source_z_min = min(sz_coords)
            source_z_max = max(sz_coords)
            
            # X MIN alignment error (should be ~0 after align_objects X MIN)
            x_min_error = source_x_min - target_x_min
            print(f"X MIN ALIGNMENT ERROR: {x_min_error:.6f} (source_x_min={source_x_min:.6f}, target_x_min={target_x_min:.6f})")
            
            # Z CONTACT GAP (should be ~0 after place_on Z)
            z_gap = source_z_min - target_z_max
            print(f"Z CONTACT GAP: {z_gap:.6f} (source_z_min={source_z_min:.6f}, target_z_max={target_z_max:.6f})")
            
            # Note: Z CENTER is NOT checked because place_on Z moves the source, 
            # changing its Z center. Z CENTER and Z CONTACT are mutually exclusive 
            # for objects of different heights.

print("=" * 80)
print("COMBINED TEST DIAGNOSTIC COMPLETE")
print("=" * 80)