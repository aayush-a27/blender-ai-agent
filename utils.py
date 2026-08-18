import bpy
from mathutils import Vector


def get_active_object():
    """Return the active object or None."""
    return bpy.context.active_object


def get_selected_objects():
    """Return list of selected objects."""
    return list(bpy.context.selected_objects)


def deselect_all():
    """Deselect all objects."""
    bpy.ops.object.select_all(action='DESELECT')


def select_object(obj):
    """Select a specific object and make it active."""
    deselect_all()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def create_object_at_cursor(object_type, **kwargs):
    """
    Create a primitive object at the 3D cursor location.
    
    Args:
        object_type: 'cube', 'sphere', 'cylinder', etc.
        **kwargs: Additional arguments passed to the primitive add operator
    
    Returns:
        The created object
    """
    cursor_loc = bpy.context.scene.cursor.location
    
    if object_type == 'cube':
        bpy.ops.mesh.primitive_cube_add(location=cursor_loc, **kwargs)
    elif object_type == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(location=cursor_loc, **kwargs)
    elif object_type == 'cylinder':
        bpy.ops.mesh.primitive_cylinder_add(location=cursor_loc, **kwargs)
    else:
        raise ValueError(f"Unknown object type: {object_type}")
    
    return bpy.context.active_object


def delete_objects(objects):
    """Delete a list of objects."""
    if not objects:
        return 0
    
    deselect_all()
    for obj in objects:
        obj.select_set(True)
    
    count = len(objects)
    bpy.ops.object.delete()
    return count


def clear_scene():
    """Delete all mesh objects in the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()