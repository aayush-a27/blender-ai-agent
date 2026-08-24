import bpy
from mathutils import Vector

print("=" * 80)
print("SHADING DIAGNOSTIC")
print("=" * 80)

root = bpy.data.objects.get("ShadingTest")
if not root:
    print("ERROR: ShadingTest root not found")
else:
    print(f"ROOT: {root.name}")
    print(f"  location: {root.location}")
    print(f"  rotation: {root.rotation_euler}")
    print(f"  scale: {root.scale}")
    print()

    cylinder = bpy.data.objects.get("ShadingTest_Cylinder")
    cube = bpy.data.objects.get("ShadingTest_Cube")
    
    if not cylinder:
        print("ERROR: ShadingTest_Cylinder not found")
    else:
        print(f"CYLINDER: {cylinder.name}")
        cylinder_bbox = [cylinder.matrix_world @ Vector(c) for c in cylinder.bound_box]
        cz_coords = [c.z for c in cylinder_bbox]
        print(f"  Z bounds: [{min(cz_coords):.6f}, {max(cz_coords):.6f}]")
        # Check smooth shading
        if cylinder.data and cylinder.data.polygons:
            smooth_count = sum(1 for p in cylinder.data.polygons if p.use_smooth)
            total = len(cylinder.data.polygons)
            print(f"  Polygons: {total}, Smooth: {smooth_count}, Flat: {total - smooth_count}")
            if total > 0:
                print(f"  Smooth ratio: {smooth_count/total*100:.1f}%")
        print()
    
    if not cube:
        print("ERROR: ShadingTest_Cube not found")
    else:
        print(f"CUBE: {cube.name}")
        cube_bbox = [cube.matrix_world @ Vector(c) for c in cube.bound_box]
        cx_coords = [c.x for c in cube_bbox]
        cy_coords = [c.y for c in cube_bbox]
        cz_coords = [c.z for c in cube_bbox]
        print(f"  X bounds: [{min(cx_coords):.6f}, {max(cx_coords):.6f}]")
        print(f"  Y bounds: [{min(cy_coords):.6f}, {max(cy_coords):.6f}]")
        print(f"  Z bounds: [{min(cz_coords):.6f}, {max(cz_coords):.6f}]")
        # Check flat shading
        if cube.data and cube.data.polygons:
            smooth_count = sum(1 for p in cube.data.polygons if p.use_smooth)
            total = len(cube.data.polygons)
            print(f"  Polygons: {total}, Smooth: {smooth_count}, Flat: {total - smooth_count}")
            if total > 0:
                print(f"  Smooth ratio: {smooth_count/total*100:.1f}%")

print("=" * 80)
print("SHADING DIAGNOSTIC COMPLETE")
print("=" * 80)