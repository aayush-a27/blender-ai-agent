# Blender AI Agent - Action Validation & Execution
import bpy
from mathutils import Vector, Color, Euler
from typing import Dict, Any, Tuple, Optional, List
from ..utils import create_object_at_cursor
from ..materials import procedural
from . import operations as bpy_operations
from . import capabilities
from .client import _log_diagnostic


# Supported action types
SUPPORTED_ACTIONS = {
    "create_object", "delete_selected", "clear_scene",
    "move_object", "rotate_object", "scale_object",
    "create_material", "apply_material", "set_material_color",
    "bpy_op", "create_light",
    "create_plane", "create_camera", "set_world_color",
    "create_collection", "join_objects", "duplicate_object",
    # v0.5 - Group/Asset actions
    "select_group", "move_group", "rotate_group", "scale_group",
    "set_group_dimensions", "delete_group", "parent_objects", "unparent_objects",
    # v0.5 - Asset creation
    "create_empty",
}
SUPPORTED_OBJECT_TYPES = {"cube", "sphere", "cylinder", "cone", "torus"}

# Supported material types for V5.1
SUPPORTED_MATERIAL_TYPES = {"default", "wood", "metal", "plastic"}

# Supported wood presets for V5.2
SUPPORTED_WOOD_PRESETS = {"wood", "light_wood", "dark_wood"}

# Supported targets for apply_material
SUPPORTED_TARGETS = {"active_object", "selected_objects"}


class ValidationError(Exception):
    pass


def validate_action(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the JSON action from the AI model.
    
    Returns validated action dict with defaults filled in.
    Raises ValidationError if invalid.
    """
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")

    action = data.get("action")
    if not action:
        raise ValidationError("Missing 'action' field")
    
    if action not in SUPPORTED_ACTIONS:
        raise ValidationError(f"Unsupported action: {action}. Supported: {SUPPORTED_ACTIONS}")

    if action == "create_object":
        return _validate_create_object(data)
    elif action == "delete_selected":
        return {"action": "delete_selected"}
    elif action == "clear_scene":
        return {"action": "clear_scene"}
    elif action == "move_object":
        return _validate_move_object(data)
    elif action == "rotate_object":
        return _validate_rotate_object(data)
    elif action == "scale_object":
        return _validate_scale_object(data)
    elif action == "create_material":
        return _validate_create_material(data)
    elif action == "apply_material":
        return _validate_apply_material(data)
    elif action == "set_material_color":
        return _validate_set_material_color(data)
    elif action == "bpy_op":
        return _validate_bpy_op(data)
    elif action == "create_light":
        return _validate_create_light(data)
    elif action == "create_plane":
        return _validate_create_plane(data)
    elif action == "create_camera":
        return _validate_create_camera(data)
    elif action == "set_world_color":
        return _validate_set_world_color(data)
    elif action == "create_collection":
        return _validate_create_collection(data)
    elif action == "join_objects":
        return _validate_join_objects(data)
    elif action == "duplicate_object":
        return _validate_duplicate_object(data)
    elif action == "create_empty":
        return _validate_create_empty(data)
    elif action == "select_group":
        return _validate_select_group(data)
    elif action == "move_group":
        return _validate_move_group(data)
    elif action == "rotate_group":
        return _validate_rotate_group(data)
    elif action == "scale_group":
        return _validate_scale_group(data)
    elif action == "set_group_dimensions":
        return _validate_set_group_dimensions(data)
    elif action == "delete_group":
        return _validate_delete_group(data)
    elif action == "parent_objects":
        return _validate_parent_objects(data)
    elif action == "unparent_objects":
        return _validate_unparent_objects(data)
    
    raise ValidationError(f"Unknown action: {action}")


def _validate_select_group(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate select_group action - selects all components of a logical group."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "select_group":
        raise ValidationError(f"Expected action 'select_group', got '{data.get('action')}'")
    
    group_name = data.get("group_name")
    if not group_name:
        raise ValidationError("select_group requires 'group_name' field")
    if not isinstance(group_name, str):
        raise ValidationError("'group_name' must be a string")
    
    return {
        "action": "select_group",
        "group_name": group_name,
    }


def _validate_move_group(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate move_group action."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "move_group":
        raise ValidationError(f"Expected action 'move_group', got '{data.get('action')}'")
    
    group_name = data.get("group_name")
    if not group_name:
        raise ValidationError("move_group requires 'group_name' field")
    if not isinstance(group_name, str):
        raise ValidationError("'group_name' must be a string")
    
    delta = data.get("delta")
    if delta is None:
        raise ValidationError("move_group requires 'delta' array")
    
    validated_delta = _validate_vector3(delta, "delta", default=None)
    if validated_delta is None:
        raise ValidationError("move_group 'delta' must be an array of 3 numbers")
    
    return {
        "action": "move_group",
        "group_name": group_name,
        "delta": validated_delta,
    }


def _validate_rotate_group(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate rotate_group action."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "rotate_group":
        raise ValidationError(f"Expected action 'rotate_group', got '{data.get('action')}'")
    
    group_name = data.get("group_name")
    if not group_name:
        raise ValidationError("rotate_group requires 'group_name' field")
    if not isinstance(group_name, str):
        raise ValidationError("'group_name' must be a string")
    
    rotation_delta = data.get("rotation_delta")
    if rotation_delta is None:
        raise ValidationError("rotate_group requires 'rotation_delta' array")
    
    validated_delta = _validate_vector3(rotation_delta, "rotation_delta", default=None)
    if validated_delta is None:
        raise ValidationError("rotate_group 'rotation_delta' must be an array of 3 numbers")
    
    return {
        "action": "rotate_group",
        "group_name": group_name,
        "rotation_delta": validated_delta,
    }


def _validate_scale_group(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate scale_group action."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "scale_group":
        raise ValidationError(f"Expected action 'scale_group', got '{data.get('action')}'")
    
    group_name = data.get("group_name")
    if not group_name:
        raise ValidationError("scale_group requires 'group_name' field")
    if not isinstance(group_name, str):
        raise ValidationError("'group_name' must be a string")
    
    scale_factor = data.get("scale_factor")
    if scale_factor is None:
        raise ValidationError("scale_group requires 'scale_factor' array")
    
    validated_factor = _validate_vector3(scale_factor, "scale_factor", default=None)
    if validated_factor is None:
        raise ValidationError("scale_group 'scale_factor' must be an array of 3 numbers")
    
    # Ensure scale factors are positive
    for i, v in enumerate(validated_factor):
        if v <= 0:
            raise ValidationError(f"scale_group 'scale_factor[{i}]' must be positive")
    
    return {
        "action": "scale_group",
        "group_name": group_name,
        "scale_factor": validated_factor,
    }


def _validate_set_group_dimensions(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate set_group_dimensions action."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "set_group_dimensions":
        raise ValidationError(f"Expected action 'set_group_dimensions', got '{data.get('action')}'")
    
    group_name = data.get("group_name")
    if not group_name:
        raise ValidationError("set_group_dimensions requires 'group_name' field")
    if not isinstance(group_name, str):
        raise ValidationError("'group_name' must be a string")
    
    # At least one dimension must be specified
    if "width" not in data and "depth" not in data and "height" not in data:
        raise ValidationError("set_group_dimensions requires at least one of: width, depth, height")
    
    validated = {
        "action": "set_group_dimensions",
        "group_name": group_name,
    }
    
    # Validate each dimension if provided
    for dim in ["width", "depth", "height"]:
        if dim in data:
            val = data[dim]
            if not isinstance(val, (int, float)):
                raise ValidationError(f"'{dim}' must be a number")
            if val <= 0:
                raise ValidationError(f"'{dim}' must be > 0")
            validated[dim] = float(val)
    
    return validated


def _validate_delete_group(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate delete_group action."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "delete_group":
        raise ValidationError(f"Expected action 'delete_group', got '{data.get('action')}'")
    
    group_name = data.get("group_name")
    if not group_name:
        raise ValidationError("delete_group requires 'group_name' field")
    if not isinstance(group_name, str):
        raise ValidationError("'group_name' must be a string")
    
    return {
        "action": "delete_group",
        "group_name": group_name,
    }


def _validate_parent_objects(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parent_objects action - creates parent-child relationships."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "parent_objects":
        raise ValidationError(f"Expected action 'parent_objects', got '{data.get('action')}'")
    
    parent_name = data.get("parent")
    if not parent_name:
        raise ValidationError("parent_objects requires 'parent' field")
    if not isinstance(parent_name, str):
        raise ValidationError("'parent' must be a string")
    
    children = data.get("children")
    if not children:
        raise ValidationError("parent_objects requires 'children' array")
    if not isinstance(children, list):
        raise ValidationError("'children' must be an array of object names")
    if len(children) == 0:
        raise ValidationError("'children' must contain at least one object name")
    
    for i, child in enumerate(children):
        if not isinstance(child, str):
            raise ValidationError(f"children[{i}] must be a string (object name)")
    
    return {
        "action": "parent_objects",
        "parent": parent_name,
        "children": children,
    }


def _validate_unparent_objects(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate unparent_objects action - removes parent-child relationships."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "unparent_objects":
        raise ValidationError(f"Expected action 'unparent_objects', got '{data.get('action')}'")
    
    children = data.get("children")
    if not children:
        raise ValidationError("unparent_objects requires 'children' array")
    if not isinstance(children, list):
        raise ValidationError("'children' must be an array of object names")
    if len(children) == 0:
        raise ValidationError("'children' must contain at least one object name")
    
    for i, child in enumerate(children):
        if not isinstance(child, str):
            raise ValidationError(f"children[{i}] must be a string (object name)")
    
    keep_transform = data.get("keep_transform", True)
    if not isinstance(keep_transform, bool):
        raise ValidationError("'keep_transform' must be a boolean")
    
    return {
        "action": "unparent_objects",
        "children": children,
        "keep_transform": keep_transform,
    }


def _validate_create_object(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate create_object action with all parameters."""
    obj_type = data.get("object_type")
    if not obj_type:
        raise ValidationError("create_object requires 'object_type'")
    
    if obj_type not in SUPPORTED_OBJECT_TYPES:
        raise ValidationError(f"Unsupported object_type: {obj_type}. Supported: {SUPPORTED_OBJECT_TYPES}")

    validated = {
        "action": "create_object",
        "object_type": obj_type,
        "location": _validate_vector3(data.get("location"), "location", default=(0, 0, 0)),
        "rotation": _validate_vector3(data.get("rotation"), "rotation", default=(0, 0, 0)),
        "scale": _validate_vector3(data.get("scale"), "scale", default=(1, 1, 1)),
        "color": _validate_color(data.get("color"), default=(0.8, 0.8, 0.8, 1.0)),
    }

    # Optional name field
    name = data.get("name")
    if name is not None:
        if not isinstance(name, str):
            raise ValidationError("'name' must be a string")
        name = name.strip()
        if not name:
            raise ValidationError("'name' cannot be empty or whitespace")
        validated["name"] = name

    # Primitive-specific parameters
    if obj_type == "torus":
        validated["major_radius"] = _validate_positive_number(data.get("major_radius"), "major_radius", default=1.0)
        validated["minor_radius"] = _validate_positive_number(data.get("minor_radius"), "minor_radius", default=0.25)
        validated["major_segments"] = _validate_positive_int(data.get("major_segments"), "major_segments", default=48)
        validated["minor_segments"] = _validate_positive_int(data.get("minor_segments"), "minor_segments", default=16)
    elif obj_type == "cone":
        validated["radius1"] = _validate_positive_number(data.get("radius1"), "radius1", default=1.0)
        validated["radius2"] = _validate_nonnegative_number(data.get("radius2"), "radius2", default=0.0)
        validated["depth"] = _validate_positive_number(data.get("depth"), "depth", default=2.0)
    elif obj_type == "cylinder":
        validated["radius"] = _validate_positive_number(data.get("radius"), "radius", default=1.0)
        validated["depth"] = _validate_positive_number(data.get("depth"), "depth", default=2.0)
    elif obj_type == "sphere":
        validated["radius"] = _validate_positive_number(data.get("radius"), "radius", default=1.0)
    elif obj_type == "cube":
        validated["size"] = _validate_positive_number(data.get("size"), "size", default=2.0)

    return validated


def _validate_move_object(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate move_object action with delta parameter."""
    target = data.get("target")
    if not target:
        raise ValidationError("move_object requires 'target' field")
    if target != "active":
        raise ValidationError("move_object only supports target: 'active'")
    
    delta = data.get("delta")
    if delta is None:
        raise ValidationError("move_object requires 'delta' array")
    
    validated_delta = _validate_vector3(delta, "delta", default=None)
    if validated_delta is None:
        raise ValidationError("move_object 'delta' must be an array of 3 numbers")
    
    return {
        "action": "move_object",
        "target": "active",
        "delta": validated_delta,
    }


def _validate_rotate_object(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate rotate_object action with rotation_delta parameter."""
    target = data.get("target")
    if not target:
        raise ValidationError("rotate_object requires 'target' field")
    if target != "active":
        raise ValidationError("rotate_object only supports target: 'active'")
    
    rotation_delta = data.get("rotation_delta")
    if rotation_delta is None:
        raise ValidationError("rotate_object requires 'rotation_delta' array")
    
    validated_delta = _validate_vector3(rotation_delta, "rotation_delta", default=None)
    if validated_delta is None:
        raise ValidationError("rotate_object 'rotation_delta' must be an array of 3 numbers")
    
    return {
        "action": "rotate_object",
        "target": "active",
        "rotation_delta": validated_delta,
    }


def _validate_scale_object(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate scale_object action with scale_factor parameter."""
    target = data.get("target")
    if not target:
        raise ValidationError("scale_object requires 'target' field")
    if target != "active":
        raise ValidationError("scale_object only supports target: 'active'")
    
    scale_factor = data.get("scale_factor")
    if scale_factor is None:
        raise ValidationError("scale_object requires 'scale_factor' array")
    
    validated_factor = _validate_vector3(scale_factor, "scale_factor", default=None)
    if validated_factor is None:
        raise ValidationError("scale_object 'scale_factor' must be an array of 3 numbers")
    
    # Ensure scale factors are positive
    for i, v in enumerate(validated_factor):
        if v <= 0:
            raise ValidationError(f"scale_object 'scale_factor[{i}]' must be positive")
    
    return {
        "action": "scale_object",
        "target": "active",
        "scale_factor": validated_factor,
    }


def _validate_create_material(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate create_material action."""
    material_name = data.get("material_name")
    if not material_name:
        raise ValidationError("create_material requires 'material_name'")
    if not isinstance(material_name, str):
        raise ValidationError("'material_name' must be a string")
    
    material_type = data.get("material_type")
    if not material_type:
        raise ValidationError("create_material requires 'material_type'")
    if material_type not in SUPPORTED_MATERIAL_TYPES:
        raise ValidationError(f"Unsupported material_type: {material_type}. Supported: {SUPPORTED_MATERIAL_TYPES}")
    
    return {
        "action": "create_material",
        "material_name": material_name,
        "material_type": material_type,
    }


def _validate_apply_material(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate apply_material action with target and material preset."""
    material = data.get("material")
    if not material:
        raise ValidationError("apply_material requires 'material' field")
    if not isinstance(material, str):
        raise ValidationError("'material' must be a string")
    
    if material not in SUPPORTED_WOOD_PRESETS:
        raise ValidationError(f"Unsupported material preset: {material}. Supported: {SUPPORTED_WOOD_PRESETS}")
    
    target = data.get("target")
    if not target:
        raise ValidationError("apply_material requires 'target' field")
    if not isinstance(target, str):
        raise ValidationError("'target' must be a string")
    if not target.strip():
        raise ValidationError("'target' cannot be empty or whitespace")
    
    # Allow "active_object", "selected_objects", or any object name
    if target not in SUPPORTED_TARGETS:
        # Allow any non-empty string as a potential object name
        # We don't validate object existence here since the object may be created
        # by a previous action in the same scene plan
        pass
    
    return {
        "action": "apply_material",
        "material": material,
        "target": target,
    }


def _validate_set_material_color(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate set_material_color action."""
    object_target = data.get("object_target")
    if not object_target:
        raise ValidationError("set_material_color requires 'object_target'")
    if object_target != "active":
        raise ValidationError("set_material_color only supports object_target: 'active'")
    
    color = data.get("color")
    if color is None:
        raise ValidationError("set_material_color requires 'color' array")
    
    validated_color = _validate_color(color, default=None)
    if validated_color is None:
        raise ValidationError("set_material_color 'color' must be an array of 4 numbers [r, g, b, a]")
    
    return {
        "action": "set_material_color",
        "object_target": "active",
        "color": validated_color,
    }


def _validate_bpy_op(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate bpy_op action with whitelisted operator and params."""
    operator = data.get("operator")
    if not operator:
        raise ValidationError("bpy_op requires 'operator' field")
    if not isinstance(operator, str):
        raise ValidationError("'operator' must be a string")
    
    params = data.get("params")
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        raise ValidationError("'params' must be an object")
    
    try:
        validated = bpy_operations.validate_bpy_operation(operator, params)
        return validated
    except ValueError as e:
        raise ValidationError(str(e))


def _validate_create_plane(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate create_plane action with high-level parameters."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "create_plane":
        raise ValidationError(f"Expected action 'create_plane', got '{data.get('action')}'")
    
    # Validate size
    size = data.get("size")
    if size is not None:
        if not isinstance(size, (int, float)):
            raise ValidationError("'size' must be a number")
        if size <= 0:
            raise ValidationError("'size' must be > 0")
    
    # Validate location
    location = data.get("location")
    if location is not None:
        if not isinstance(location, (list, tuple)) or len(location) != 3:
            raise ValueError("'location' must be an array of 3 numbers [x, y, z]")
        for i, v in enumerate(location):
            if not isinstance(v, (int, float)):
                raise ValueError(f"location[{i}] must be a number")
    
    # Validate rotation
    rotation = data.get("rotation")
    if rotation is not None:
        if not isinstance(rotation, (list, tuple)) or len(rotation) != 3:
            raise ValueError("'rotation' must be an array of 3 numbers [x, y, z] in radians")
        for i, v in enumerate(rotation):
            if not isinstance(v, (int, float)):
                raise ValueError(f"rotation[{i}] must be a number")
    
    # Build validated action
    validated = {
        "action": "create_plane",
    }
    
    # Optional parameters with defaults
    if "size" in data:
        validated["size"] = float(data["size"])
    else:
        validated["size"] = 2.0
    
    if "location" in data:
        validated["location"] = tuple(float(v) for v in data["location"])
    else:
        validated["location"] = (0.0, 0.0, 0.0)
    
    if "rotation" in data:
        validated["rotation"] = tuple(float(v) for v in data["rotation"])
    else:
        validated["rotation"] = (0.0, 0.0, 0.0)
    
    if "scale" in data:
        validated["scale"] = tuple(float(v) for v in data["scale"])
    else:
        validated["scale"] = (1.0, 1.0, 1.0)
    
    if "name" in data:
        validated["name"] = str(data["name"])
    
    return validated


def _validate_create_camera(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate create_camera action with high-level parameters."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "create_camera":
        raise ValidationError(f"Expected action 'create_camera', got '{data.get('action')}'")
    
    # Validate location
    location = data.get("location")
    if location is not None:
        if not isinstance(location, (list, tuple)) or len(location) != 3:
            raise ValueError("'location' must be an array of 3 numbers [x, y, z]")
        for i, v in enumerate(location):
            if not isinstance(v, (int, float)):
                raise ValueError(f"location[{i}] must be a number")
    
    # Validate rotation
    rotation = data.get("rotation")
    if rotation is not None:
        if not isinstance(rotation, (list, tuple)) or len(rotation) != 3:
            raise ValueError("'rotation' must be an array of 3 numbers [x, y, z] in radians")
        for i, v in enumerate(rotation):
            if not isinstance(v, (int, float)):
                raise ValueError(f"rotation[{i}] must be a number")
    
    # Validate lens (focal length in mm)
    lens = data.get("lens")
    if lens is not None:
        if not isinstance(lens, (int, float)):
            raise ValidationError("'lens' must be a number")
        if lens <= 0:
            raise ValidationError("'lens' must be > 0")
    
    # Validate sensor_width (for focal length calculations)
    sensor_width = data.get("sensor_width")
    if sensor_width is not None:
        if not isinstance(sensor_width, (int, float)):
            raise ValidationError("'sensor_width' must be a number")
        if sensor_width <= 0:
            raise ValidationError("'sensor_width' must be > 0")
    
    # Build validated action
    validated = {
        "action": "create_camera",
    }
    
    # Optional parameters with defaults
    if "location" in data:
        validated["location"] = tuple(float(v) for v in data["location"])
    else:
        validated["location"] = (0.0, 0.0, 0.0)
    
    if "rotation" in data:
        validated["rotation"] = tuple(float(v) for v in data["rotation"])
    else:
        validated["rotation"] = (0.0, 0.0, 0.0)
    
    if "lens" in data:
        validated["lens"] = float(data["lens"])
    else:
        validated["lens"] = 50.0
    
    if "sensor_width" in data:
        validated["sensor_width"] = float(data["sensor_width"])
    else:
        validated["sensor_width"] = 36.0
    
    if "name" in data:
        validated["name"] = str(data["name"])
    
    return validated


def _validate_set_world_color(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate set_world_color action with high-level parameters."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "set_world_color":
        raise ValidationError(f"Expected action 'set_world_color', got '{data.get('action')}'")
    
    # Validate color
    color = data.get("color")
    if color is None:
        raise ValidationError("set_world_color requires 'color' array")
    
    validated_color = _validate_color(color, default=None)
    if validated_color is None:
        raise ValidationError("set_world_color 'color' must be an array of 4 numbers [r, g, b, a]")
    
    # Validate strength (emission strength)
    strength = data.get("strength")
    if strength is not None:
        if not isinstance(strength, (int, float)):
            raise ValidationError("'strength' must be a number")
        if strength < 0:
            raise ValidationError("'strength' must be >= 0")
    
    # Build validated action
    validated = {
        "action": "set_world_color",
        "color": validated_color,
    }
    
    if "strength" in data:
        validated["strength"] = float(data["strength"])
    else:
        validated["strength"] = 1.0
    
    return validated


def _validate_create_collection(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate create_collection action."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "create_collection":
        raise ValidationError(f"Expected action 'create_collection', got '{data.get('action')}'")
    
    name = data.get("name")
    if not name:
        raise ValidationError("create_collection requires 'name' field")
    if not isinstance(name, str):
        raise ValidationError("'name' must be a string")
    
    parent = data.get("parent")
    if parent is not None and not isinstance(parent, str):
        raise ValidationError("'parent' must be a string (collection name)")
    
    return {
        "action": "create_collection",
        "name": name,
        "parent": parent,
    }


def _validate_join_objects(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate join_objects action."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "join_objects":
        raise ValidationError(f"Expected action 'join_objects', got '{data.get('action')}'")
    
    target = data.get("target")
    if not target:
        raise ValidationError("join_objects requires 'target' field")
    if not isinstance(target, str):
        raise ValidationError("'target' must be a string (object name)")
    
    sources = data.get("sources")
    if not sources:
        raise ValidationError("join_objects requires 'sources' array")
    if not isinstance(sources, list):
        raise ValidationError("'sources' must be an array of object names")
    if len(sources) < 1:
        raise ValidationError("'sources' must contain at least one object name")
    
    for i, src in enumerate(sources):
        if not isinstance(src, str):
            raise ValidationError(f"sources[{i}] must be a string (object name)")
    
    return {
        "action": "join_objects",
        "target": target,
        "sources": sources,
    }


def _validate_duplicate_object(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate duplicate_object action."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "duplicate_object":
        raise ValidationError(f"Expected action 'duplicate_object', got '{data.get('action')}'")
    
    source = data.get("source")
    if not source:
        raise ValidationError("duplicate_object requires 'source' field")
    if not isinstance(source, str):
        raise ValidationError("'source' must be a string (object name)")
    
    location = data.get("location")
    if location is not None:
        if not isinstance(location, (list, tuple)) or len(location) != 3:
            raise ValueError("'location' must be an array of 3 numbers [x, y, z]")
        for i, v in enumerate(location):
            if not isinstance(v, (int, float)):
                raise ValueError(f"location[{i}] must be a number")
    
    rotation = data.get("rotation")
    if rotation is not None:
        if not isinstance(rotation, (list, tuple)) or len(rotation) != 3:
            raise ValueError("'rotation' must be an array of 3 numbers [x, y, z] in radians")
        for i, v in enumerate(rotation):
            if not isinstance(v, (int, float)):
                raise ValueError(f"rotation[{i}] must be a number")
    
    scale = data.get("scale")
    if scale is not None:
        if not isinstance(scale, (list, tuple)) or len(scale) != 3:
            raise ValueError("'scale' must be an array of 3 numbers [x, y, z]")
        for i, v in enumerate(scale):
            if not isinstance(v, (int, float)):
                raise ValueError(f"scale[{i}] must be a number")
            if v <= 0:
                raise ValidationError(f"scale[{i}] must be > 0")
    
    name = data.get("name")
    if name is not None and not isinstance(name, str):
        raise ValidationError("'name' must be a string")
    
    validated = {
        "action": "duplicate_object",
        "source": source,
    }
    
    if "location" in data:
        validated["location"] = tuple(float(v) for v in data["location"])
    else:
        validated["location"] = (0.0, 0.0, 0.0)
    
    if "rotation" in data:
        validated["rotation"] = tuple(float(v) for v in data["rotation"])
    else:
        validated["rotation"] = (0.0, 0.0, 0.0)
    
    if "scale" in data:
        validated["scale"] = tuple(float(v) for v in data["scale"])
    else:
        validated["scale"] = (1.0, 1.0, 1.0)
    
    if "name" in data:
        validated["name"] = str(data["name"])
    
    return validated


def _validate_create_empty(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate create_empty action with high-level parameters."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "create_empty":
        raise ValidationError(f"Expected action 'create_empty', got '{data.get('action')}'")
    
    # Validate empty type
    empty_type = data.get("empty_type")
    if empty_type is not None:
        if not isinstance(empty_type, str):
            raise ValidationError("'empty_type' must be a string")
        if empty_type not in {"PLAIN_AXES", "ARROWS", "SINGLE_ARROW", "CIRCLE", "CUBE", "SPHERE", "CONE"}:
            raise ValidationError(f"Unsupported empty_type: {empty_type}. Supported: PLAIN_AXES, ARROWS, SINGLE_ARROW, CIRCLE, CUBE, SPHERE, CONE")
    
    # Validate location
    location = data.get("location")
    if location is not None:
        if not isinstance(location, (list, tuple)) or len(location) != 3:
            raise ValueError("'location' must be an array of 3 numbers [x, y, z]")
        for i, v in enumerate(location):
            if not isinstance(v, (int, float)):
                raise ValueError(f"location[{i}] must be a number")
    
    # Validate rotation
    rotation = data.get("rotation")
    if rotation is not None:
        if not isinstance(rotation, (list, tuple)) or len(rotation) != 3:
            raise ValueError("'rotation' must be an array of 3 numbers [x, y, z] in radians")
        for i, v in enumerate(rotation):
            if not isinstance(v, (int, float)):
                raise ValueError(f"rotation[{i}] must be a number")
    
    # Validate scale
    scale = data.get("scale")
    if scale is not None:
        if not isinstance(scale, (list, tuple)) or len(scale) != 3:
            raise ValueError("'scale' must be an array of 3 numbers [x, y, z]")
        for i, v in enumerate(scale):
            if not isinstance(v, (int, float)):
                raise ValueError(f"scale[{i}] must be a number")
            if v <= 0:
                raise ValidationError(f"scale[{i}] must be > 0")
    
    # Validate radius
    radius = data.get("radius")
    if radius is not None:
        if not isinstance(radius, (int, float)):
            raise ValidationError("'radius' must be a number")
        if radius <= 0:
            raise ValidationError("'radius' must be > 0")
    
    name = data.get("name")
    if name is not None and not isinstance(name, str):
        raise ValidationError("'name' must be a string")
    
    validated = {
        "action": "create_empty",
    }
    
    # Optional parameters with defaults
    if "empty_type" in data:
        validated["empty_type"] = data["empty_type"]
    else:
        validated["empty_type"] = "PLAIN_AXES"
    
    if "location" in data:
        validated["location"] = tuple(float(v) for v in data["location"])
    else:
        validated["location"] = (0.0, 0.0, 0.0)
    
    if "rotation" in data:
        validated["rotation"] = tuple(float(v) for v in data["rotation"])
    else:
        validated["rotation"] = (0.0, 0.0, 0.0)
    
    if "scale" in data:
        validated["scale"] = tuple(float(v) for v in data["scale"])
    else:
        validated["scale"] = (1.0, 1.0, 1.0)
    
    if "radius" in data:
        validated["radius"] = float(data["radius"])
    else:
        validated["radius"] = 1.0
    
    if "name" in data:
        validated["name"] = str(data["name"])
    
    return validated


def _validate_create_light(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate create_light action with high-level parameters."""
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    action = data.get("action")
    if action != "create_light":
        raise ValidationError(f"Expected action 'create_light', got '{data.get('action')}'")
    
    # Validate light_type
    light_type = data.get("light_type")
    if not light_type:
        raise ValidationError("create_light requires 'light_type' field")
    if light_type not in {"POINT", "SUN", "SPOT", "AREA"}:
        raise ValidationError(f"Unsupported light_type: {light_type}. Supported: POINT, SUN, SPOT, AREA")
    
    # Validate brightness (maps to energy)
    brightness = data.get("brightness")
    if brightness is None:
        raise ValidationError("create_light requires 'brightness' field")
    if not isinstance(brightness, (int, float)):
        raise ValidationError("'brightness' must be a number")
    if brightness < 0:
        raise ValidationError("'brightness' must be >= 0")
    
    # Validate color
    color = data.get("color")
    if color is not None:
        if not isinstance(color, (list, tuple)) or len(color) != 3:
            raise ValueError("'color' must be an array of 3 numbers [r, g, b]")
        for i, v in enumerate(color):
            if not isinstance(v, (int, float)):
                raise ValueError(f"color[{i}] must be a number")
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"color[{i}] must be between 0.0 and 1.0")
    
    # Validate location
    location = data.get("location")
    if location is not None:
        if not isinstance(location, (list, tuple)) or len(location) != 3:
            raise ValueError("'location' must be an array of 3 numbers [x, y, z]")
        for i, v in enumerate(location):
            if not isinstance(v, (int, float)):
                raise ValueError(f"location[{i}] must be a number")
    
    # Validate rotation
    rotation = data.get("rotation")
    if rotation is not None:
        if not isinstance(rotation, (list, tuple)) or len(rotation) != 3:
            raise ValueError("'rotation' must be an array of 3 numbers [x, y, z] in radians")
        for i, v in enumerate(rotation):
            if not isinstance(v, (int, float)):
                raise ValueError(f"rotation[{i}] must be a number")
    
    # Build validated action
    validated = {
        "action": "create_light",
        "light_type": data["light_type"],
        "brightness": float(data["brightness"]),
    }
    
    # Optional parameters with defaults
    if "color" in data:
        validated["color"] = tuple(float(c) for c in data["color"])
    else:
        validated["color"] = (1.0, 1.0, 1.0)
    
    if "location" in data:
        validated["location"] = tuple(float(v) for v in data["location"])
    else:
        validated["location"] = (0.0, 0.0, 0.0)
    
    if "rotation" in data:
        validated["rotation"] = tuple(float(v) for v in data["rotation"])
    else:
        validated["rotation"] = (0.0, 0.0, 0.0)
    
    return validated


def _validate_vector3(value: Any, field_name: str, default: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Validate a 3-element numeric array."""
    if value is None:
        return default
    
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValidationError(f"'{field_name}' must be an array of 3 numbers")
    
    result = []
    for i, v in enumerate(value):
        if not isinstance(v, (int, float)):
            raise ValidationError(f"'{field_name}[{i}]' must be a number")
        if not (float("-inf") < v < float("inf")):
            raise ValidationError(f"'{field_name}[{i}]' must be finite")
        result.append(float(v))
    
    return tuple(result)


def _validate_color(value: Any, default: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """Validate a 4-element color array (RGBA, 0-1)."""
    if value is None:
        return default
    
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValidationError("'color' must be an array of 4 numbers [r, g, b, a]")
    
    result = []
    for i, v in enumerate(value):
        if not isinstance(v, (int, float)):
            raise ValidationError(f"'color[{i}]' must be a number")
        if not (0.0 <= v <= 1.0):
            raise ValidationError(f"'color[{i}]' must be between 0.0 and 1.0")
        result.append(float(v))
    
    return tuple(result)


def _validate_positive_number(value: Any, field_name: str, default: float) -> float:
    """Validate a positive number parameter."""
    if value is None:
        return default
    if not isinstance(value, (int, float)):
        raise ValidationError(f"'{field_name}' must be a number")
    if value <= 0:
        raise ValidationError(f"'{field_name}' must be > 0")
    return float(value)


def _validate_nonnegative_number(value: Any, field_name: str, default: float) -> float:
    """Validate a non-negative number parameter."""
    if value is None:
        return default
    if not isinstance(value, (int, float)):
        raise ValidationError(f"'{field_name}' must be a number")
    if value < 0:
        raise ValidationError(f"'{field_name}' must be >= 0")
    return float(value)


def _validate_positive_int(value: Any, field_name: str, default: int) -> int:
    """Validate a positive integer parameter."""
    if value is None:
        return default
    if not isinstance(value, int):
        raise ValidationError(f"'{field_name}' must be an integer")
    if value <= 0:
        raise ValidationError(f"'{field_name}' must be > 0")
    return value


def execute_action(action: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Execute a validated action in Blender.
    
    Returns:
        (success: bool, message: str)
    """
    try:
        action_type = action["action"]
        
        if action_type == "create_object":
            return _execute_create_object(action)
        elif action_type == "delete_selected":
            return _execute_delete_selected()
        elif action_type == "clear_scene":
            return _execute_clear_scene()
        elif action_type == "move_object":
            return _execute_move_object(action)
        elif action_type == "rotate_object":
            return _execute_rotate_object(action)
        elif action_type == "scale_object":
            return _execute_scale_object(action)
        elif action_type == "create_material":
            return _execute_create_material(action)
        elif action_type == "apply_material":
            return _execute_apply_material(action)
        elif action_type == "set_material_color":
            return _execute_set_material_color(action)
        elif action_type == "bpy_op":
            return _execute_bpy_op(action)
        elif action_type == "create_light":
            return _execute_create_light(action)
        elif action_type == "create_plane":
            return _execute_create_plane(action)
        elif action_type == "create_camera":
            return _execute_create_camera(action)
        elif action_type == "set_world_color":
            return _execute_set_world_color(action)
        elif action_type == "create_collection":
            return _execute_create_collection(action)
        elif action_type == "join_objects":
            return _execute_join_objects(action)
        elif action_type == "duplicate_object":
            return _execute_duplicate_object(action)
        elif action_type == "create_empty":
            return _execute_create_empty(action)
        elif action_type == "select_group":
            return _execute_select_group(action)
        elif action_type == "move_group":
            return _execute_move_group(action)
        elif action_type == "rotate_group":
            return _execute_rotate_group(action)
        elif action_type == "scale_group":
            return _execute_scale_group(action)
        elif action_type == "set_group_dimensions":
            return _execute_set_group_dimensions(action)
        elif action_type == "delete_group":
            return _execute_delete_group(action)
        elif action_type == "parent_objects":
            return _execute_parent_objects(action)
        elif action_type == "unparent_objects":
            return _execute_unparent_objects(action)
        else:
            return False, f"Unknown action: {action_type}"
    
    except Exception as e:
        return False, f"Execution failed: {e}"


def _get_active_object_or_error():
    """Get the active object or return error tuple."""
    obj = bpy.context.active_object
    if not obj:
        return None, "No active object. Select an object first."
    return obj, None


def _execute_move_object(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute move_object action - move active object by delta."""
    obj, error = _get_active_object_or_error()
    if error:
        return False, error
    
    delta = action["delta"]
    obj.location.x += delta[0]
    obj.location.y += delta[1]
    obj.location.z += delta[2]
    
    return True, f"Moved '{obj.name}' by {delta}"


def _execute_rotate_object(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute rotate_object action - rotate active object by delta (radians)."""
    obj, error = _get_active_object_or_error()
    if error:
        return False, error
    
    rotation_delta = action["rotation_delta"]
    obj.rotation_euler.x += rotation_delta[0]
    obj.rotation_euler.y += rotation_delta[1]
    obj.rotation_euler.z += rotation_delta[2]
    
    return True, f"Rotated '{obj.name}' by {rotation_delta} radians"


def _execute_scale_object(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute scale_object action - scale active object by factor."""
    obj, error = _get_active_object_or_error()
    if error:
        return False, error
    
    scale_factor = action["scale_factor"]
    obj.scale.x *= scale_factor[0]
    obj.scale.y *= scale_factor[1]
    obj.scale.z *= scale_factor[2]
    
    return True, f"Scaled '{obj.name}' by factor {scale_factor}"


def _execute_create_object(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute create_object action."""
    obj_type = action["object_type"]
    location = Vector(action["location"])
    rotation = action["rotation"]
    scale = action["scale"]
    color = action["color"]
    name = action.get("name")
    
    # Create object at specified location (not cursor)
    if obj_type == "cube":
        size = action.get("size", 2.0)
        bpy.ops.mesh.primitive_cube_add(size=size, location=location, rotation=rotation, scale=scale)
    elif obj_type == "sphere":
        radius = action.get("radius", 1.0)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location, rotation=rotation, scale=scale)
    elif obj_type == "cylinder":
        radius = action.get("radius", 1.0)
        depth = action.get("depth", 2.0)
        bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=location, rotation=rotation, scale=scale)
    elif obj_type == "cone":
        radius1 = action.get("radius1", 1.0)
        radius2 = action.get("radius2", 0.0)
        depth = action.get("depth", 2.0)
        bpy.ops.mesh.primitive_cone_add(radius1=radius1, radius2=radius2, depth=depth, location=location, rotation=rotation, scale=scale)
    elif obj_type == "torus":
        major_radius = action.get("major_radius", 1.0)
        minor_radius = action.get("minor_radius", 0.25)
        major_segments = action.get("major_segments", 48)
        minor_segments = action.get("minor_segments", 16)
        # Torus operator doesn't support scale parameter, apply after creation
        bpy.ops.mesh.primitive_torus_add(
            major_radius=major_radius,
            minor_radius=minor_radius,
            major_segments=major_segments,
            minor_segments=minor_segments,
            location=location,
            rotation=rotation
        )
    else:
        return False, f"Unknown object type: {obj_type}"
    
    obj = bpy.context.active_object
    if obj:
        # Apply scale for torus (since operator doesn't support it)
        if obj_type == "torus":
            obj.scale = scale
        # Set name from action if provided
        requested_name = action.get("name")
        if requested_name:
            obj.name = requested_name
            _log_diagnostic(f"Created component: requested={requested_name}, actual={obj.name}")
        else:
            _log_diagnostic(f"Created component: {obj.name} (no name requested)")
        _apply_color(obj, color)
        return True, f"Created {obj_type} at {location}"
    return False, "Object creation failed"


def _apply_color(obj: bpy.types.Object, color: Tuple[float, float, float, float]) -> None:
    """Apply a simple material with the given color to the object."""
    mat_name = f"AI_Material_{color[0]:.2f}_{color[1]:.2f}_{color[2]:.2f}"
    mat = bpy.data.materials.get(mat_name)
    
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Alpha"].default_value = color[3]
        mat.blend_method = 'BLENDED' if color[3] < 1.0 else 'OPAQUE'
    
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def _execute_delete_selected() -> Tuple[bool, str]:
    """Execute delete_selected action."""
    selected = list(bpy.context.selected_objects)
    if not selected:
        return False, "No objects selected"
    
    count = len(selected)
    bpy.ops.object.delete()
    return True, f"Deleted {count} object(s)"


def _execute_clear_scene() -> Tuple[bool, str]:
    """Execute clear_scene action."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    return True, "Scene cleared"


def _get_or_create_material(material_name: str, material_type: str):
    """Get existing material or create a new one with the specified type."""
    mat = bpy.data.materials.get(material_name)
    if mat:
        return mat
    
    mat = bpy.data.materials.new(name=material_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    
    if not bsdf:
        return mat
    
    # Configure material based on type
    if material_type == "wood":
        bsdf.inputs["Base Color"].default_value = (0.45, 0.25, 0.12, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.55
    elif material_type == "metal":
        bsdf.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1.0)
        bsdf.inputs["Metallic"].default_value = 1.0
        bsdf.inputs["Roughness"].default_value = 0.25
    elif material_type == "plastic":
        bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.35
    else:  # default
        bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.5
    
    return mat


def _execute_create_material(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute create_material action."""
    material_name = action["material_name"]
    material_type = action["material_type"]
    
    mat = _get_or_create_material(material_name, material_type)
    return True, f"Created material '{material_name}' (type: {material_type})"


def _execute_apply_material(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute apply_material action with target and material preset."""
    material = action["material"]
    target = action["target"]
    
    if target == "active_object":
        obj, error = procedural.get_active_object_or_error()
        if error:
            return False, error
        return procedural.apply_material_to_object(obj, material)
    
    elif target == "selected_objects":
        return procedural.apply_material_to_selected(material)
    
    else:
        # Treat as object name
        obj = bpy.data.objects.get(target)
        if not obj:
            return False, f"Target object '{target}' not found"
        return procedural.apply_material_to_object(obj, material)


def _execute_set_material_color(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute set_material_color action."""
    color = action["color"]
    
    obj, error = _get_active_object_or_error()
    if error:
        return False, error
    
    # Get or create material on the object
    if obj.data.materials:
        mat = obj.data.materials[0]
    else:
        mat = bpy.data.materials.new(name="AI_Material")
        mat.use_nodes = True
        obj.data.materials.append(mat)
    
    # Ensure nodes are enabled
    if not mat.use_nodes:
        mat.use_nodes = True
    
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Alpha"].default_value = color[3]
        if color[3] < 1.0:
            mat.blend_method = 'BLENDED'
        else:
            mat.blend_method = 'OPAQUE'
        return True, f"Set color of '{obj.name}' material to {color}"
    
    return False, "Failed to set color: no Principled BSDF node found"


def _execute_bpy_op(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute a whitelisted Blender operation via bpy.ops."""
    operator = action["operator"]
    params = action.get("params", {})
    
    # Split operator into module and operator name (e.g., "object.light_add" -> "object", "light_add")
    if "." not in operator:
        return False, f"Invalid operator format: {operator}. Expected 'module.operator'"
    
    module_name, op_name = operator.split(".", 1)
    
    try:
        # Get the bpy.ops module
        ops_module = getattr(bpy.ops, module_name)
        op_func = getattr(ops_module, op_name)
        
        # Execute with validated parameters
        op_func(**params)
        
        return True, f"Executed {operator} with params: {params}"
    
    except AttributeError:
        return False, f"Blender operator not found: {operator}"
    except TypeError as e:
        return False, f"Invalid parameters for {operator}: {e}"
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution of {operator} failed: {e}"


def _execute_create_light(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute create_light action using Blender 4.0.1 API.
    
    Translates high-level parameters to Blender API:
    1. Creates light via bpy.ops.object.light_add()
    2. Configures light.data.energy (brightness)
    3. Sets light.data.color
    4. Applies rotation
    
    Args:
        action: Validated action dict
        
    Returns:
        (success: bool, message: str)
    """
    try:
        light_type = action["light_type"]
        brightness = action["brightness"]
        color = action["color"]
        location = action["location"]
        rotation = action["rotation"]
        
        # Step 1: Create light via operator (only operator args here)
        bpy.ops.object.light_add(
            type=action["light_type"],
            location=location,
            rotation=rotation
        )
        
        # Step 2: Get the created light object
        light_obj = bpy.context.active_object
        if not light_obj or light_obj.type != 'LIGHT':
            return False, "Failed to create light object"
        
        # Step 3: Configure light data (energy = brightness)
        light_obj.data.energy = action["brightness"]
        
        # Step 4: Set color
        light_obj.data.color = action["color"]
        
        # Note: rotation was already applied by light_add operator
        # No need to set rotation again
        
        return True, f"Created {action['light_type']} light with brightness {action['brightness']} at {action['location']}"
        
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_create_plane(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute create_plane action using Blender 4.0.1 API."""
    try:
        size = action["size"]
        location = action["location"]
        rotation = action["rotation"]
        scale = action["scale"]
        name = action.get("name")
        
        # Create plane via operator
        bpy.ops.mesh.primitive_plane_add(
            size=size,
            location=location,
            rotation=rotation,
            scale=scale
        )
        
        obj = bpy.context.active_object
        if not obj:
            return False, "Failed to create plane object"
        
        if name:
            obj.name = name
        
        return True, f"Created plane '{obj.name}' with size {size} at {location}"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_create_camera(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute create_camera action using Blender 4.0.1 API."""
    try:
        location = action["location"]
        rotation = action["rotation"]
        lens = action["lens"]
        sensor_width = action["sensor_width"]
        name = action.get("name")
        
        # Create camera via operator
        bpy.ops.object.camera_add(
            location=location,
            rotation=rotation
        )
        
        obj = bpy.context.active_object
        if not obj or obj.type != 'CAMERA':
            return False, "Failed to create camera object"
        
        # Configure camera data
        cam_data = obj.data
        cam_data.lens = action["lens"]
        cam_data.sensor_width = action["sensor_width"]
        
        if name:
            obj.name = name
        
        return True, f"Created camera '{obj.name}' with {lens}mm lens at {location}"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_set_world_color(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute set_world_color action using Blender 4.0.1 API."""
    try:
        color = action["color"]
        strength = action["strength"]
        
        # Get or create world
        world = bpy.context.scene.world
        if not world:
            world = bpy.data.worlds.new(name="World")
            bpy.context.scene.world = world
        
        # Enable use_nodes for world
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        
        # Clear existing nodes
        nodes.clear()
        
        # Create background node
        bg_node = nodes.new(type='ShaderNodeBackground')
        bg_node.inputs[0].default_value = color  # Color
        bg_node.inputs[1].default_value = action["strength"]  # Strength
        
        # Create output node
        output_node = nodes.new(type='ShaderNodeOutputWorld')
        
        # Link background to output
        links = world.node_tree.links
        links.new(bg_node.outputs[0], output_node.inputs[0])
        
        return True, f"Set world color to {color} with strength {action['strength']}"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_create_collection(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute create_collection action using Blender 4.0.1 API."""
    try:
        name = action["name"]
        parent_name = action.get("parent")
        
        # Check if collection already exists
        if name in bpy.data.collections:
            return False, f"Collection '{name}' already exists"
        
        # Create new collection
        collection = bpy.data.collections.new(name)
        
        # Link to parent collection or scene collection
        if parent_name:
            if parent_name not in bpy.data.collections:
                return False, f"Parent collection '{parent_name}' not found"
            parent_collection = bpy.data.collections[parent_name]
            parent_collection.children.link(collection)
        else:
            bpy.context.scene.collection.children.link(collection)
        
        return True, f"Created collection '{name}'"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_join_objects(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute join_objects action using Blender 4.0.1 API."""
    try:
        target_name = action["target"]
        source_names = action["sources"]
        
        # Get target object
        target_obj = bpy.data.objects.get(target_name)
        if not target_obj:
            return False, f"Target object '{target_name}' not found"
        
        # Get source objects
        source_objects = []
        for name in source_names:
            obj = bpy.data.objects.get(name)
            if not obj:
                return False, f"Source object '{name}' not found"
            source_objects.append(obj)
        
        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select all objects to join
        for obj in source_objects:
            obj.select_set(True)
        target_obj.select_set(True)
        
        # Set target as active
        bpy.context.view_layer.objects.active = target_obj
        
        # Join objects
        bpy.ops.object.join()
        
        return True, f"Joined {len(source_objects)} object(s) into '{target_name}'"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_duplicate_object(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute duplicate_object action using Blender 4.0.1 API."""
    try:
        source_name = action["source"]
        location = action["location"]
        rotation = action["rotation"]
        scale = action["scale"]
        name = action.get("name")
        
        # Get source object
        source_obj = bpy.data.objects.get(action["source"])
        if not source_obj:
            return False, f"Source object '{action['source']}' not found"
        
        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select source
        source_obj.select_set(True)
        bpy.context.view_layer.objects.active = source_obj
        
        # Duplicate
        bpy.ops.object.duplicate(linked=False)
        
        # Get the new object
        new_obj = bpy.context.active_object
        if not new_obj:
            return False, "Failed to duplicate object"
        
        # Apply transform
        new_obj.location = location
        new_obj.rotation_euler = rotation
        new_obj.scale = scale
        
        if name:
            new_obj.name = name
        
        return True, f"Duplicated '{action['source']}' to '{new_obj.name}' at {location}"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_create_empty(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute create_empty action using Blender 4.0.1 API."""
    try:
        empty_type = action["empty_type"]
        location = action["location"]
        rotation = action["rotation"]
        scale = action["scale"]
        radius = action["radius"]
        name = action.get("name")
        
        # Create empty via operator
        bpy.ops.object.empty_add(
            type=empty_type,
            radius=radius,
            location=location,
            rotation=rotation,
            scale=scale
        )
        
        obj = bpy.context.active_object
        if not obj or obj.type != 'EMPTY':
            return False, "Failed to create empty object"
        
        if name:
            obj.name = name
        
        _log_diagnostic(f"Created asset root: {obj.name} (type: {empty_type})")
        
        return True, f"Created empty '{obj.name}' (type: {empty_type}) at {location}"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


# =============================================================================
# v0.5 - Group/Asset Actions
# =============================================================================

def _get_group_objects(group_name: str) -> List[bpy.types.Object]:
    """Get all objects belonging to a logical group by Blender parent hierarchy.
    
    Finds the root object (named exactly like group_name) and returns it 
    plus all its descendants.
    """
    # Find root object - named exactly like the group
    root = bpy.data.objects.get(group_name)
    if not root:
        return []
    
    # Collect root and all descendants
    objects = [root]
    for obj in bpy.data.objects:
        # Check if this object is a descendant of root
        current = obj.parent
        while current:
            if current == root:
                objects.append(obj)
                break
            current = current.parent
    
    return objects


def _get_group_root(group_name: str) -> Optional[bpy.types.Object]:
    """Get the root/parent object of a group by exact name match."""
    return bpy.data.objects.get(group_name)


def _execute_select_group(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute select_group action - selects all components of a logical group."""
    try:
        group_name = action["group_name"]
        objects = _get_group_objects(group_name)
        
        if not objects:
            return False, f"No objects found for group '{group_name}'"
        
        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select all group objects
        for obj in objects:
            obj.select_set(True)
        
        # Set the group root as active
        root = _get_group_root(group_name)
        if root:
            bpy.context.view_layer.objects.active = root
        
        _log_diagnostic(f"Selected asset '{group_name}' with {len(objects)} components")
        
        return True, f"Selected {len(objects)} objects in group '{group_name}'"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_move_group(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute move_group action - moves all objects in a group together."""
    try:
        group_name = action["group_name"]
        delta = action["delta"]
        objects = _get_group_objects(group_name)
        
        if not objects:
            return False, f"No objects found for group '{group_name}'"
        
        delta_vec = Vector(delta)
        for obj in objects:
            obj.location += delta_vec
        
        _log_diagnostic(f"Moving asset '{group_name}' with {len(objects)} components by {delta}")
        
        return True, f"Moved {len(objects)} objects in group '{group_name}' by {delta}"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_rotate_group(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute rotate_group action - rotates all objects in a group around their common center."""
    try:
        group_name = action["group_name"]
        rotation_delta = action["rotation_delta"]
        objects = _get_group_objects(group_name)
        
        if not objects:
            return False, f"No objects found for group '{group_name}'"
        
        # Calculate group center
        center = Vector((0, 0, 0))
        for obj in objects:
            center += obj.location
        center /= len(objects)
        
        # Rotate each object around the group center
        rot_euler = Euler(rotation_delta)
        rot_matrix = rot_euler.to_matrix()
        
        for obj in objects:
            # Translate to origin, rotate, translate back
            offset = obj.location - center
            offset.rotate(rot_matrix)
            obj.location = center + offset
            
            # Apply rotation to object's rotation
            obj.rotation_euler.rotate(rot_matrix)
        
        _log_diagnostic(f"Rotating asset '{group_name}' with {len(objects)} components by {rotation_delta}")
        
        return True, f"Rotated {len(objects)} objects in group '{group_name}' by {rotation_delta}"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_scale_group(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute scale_group action - scales all objects in a group around their common center."""
    try:
        group_name = action["group_name"]
        scale_factor = action["scale_factor"]
        objects = _get_group_objects(group_name)
        
        if not objects:
            return False, f"No objects found for group '{group_name}'"
        
        # Calculate group center
        center = Vector((0, 0, 0))
        for obj in objects:
            center += obj.location
        center /= len(objects)
        
        scale_vec = Vector(scale_factor)
        
        for obj in objects:
            # Scale position relative to center
            offset = obj.location - center
            offset.x *= scale_factor[0]
            offset.y *= scale_factor[1]
            offset.z *= scale_factor[2]
            obj.location = center + offset
            
            # Scale object's scale
            obj.scale.x *= scale_factor[0]
            obj.scale.y *= scale_factor[1]
            obj.scale.z *= scale_factor[2]
        
        return True, f"Scaled {len(objects)} objects in group '{group_name}' by factor {scale_factor}"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_set_group_dimensions(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute set_group_dimensions action - sets dimensions of a group proportionally."""
    try:
        group_name = action["group_name"]
        objects = _get_group_objects(group_name)
        
        if not objects:
            return False, f"No objects found for group '{group_name}'"
        
        # Calculate current group bounding box
        min_coords = Vector((float('inf'), float('inf'), float('inf')))
        max_coords = Vector((float('-inf'), float('-inf'), float('-inf')))
        
        for obj in objects:
            # Use bounding box corners in world space
            for corner in obj.bound_box:
                world_corner = obj.matrix_world @ Vector(corner)
                min_coords.x = min(min_coords.x, world_corner.x)
                min_coords.y = min(min_coords.y, world_corner.y)
                min_coords.z = min(min_coords.z, world_corner.z)
                max_coords.x = max(max_coords.x, world_corner.x)
                max_coords.y = max(max_coords.y, world_corner.y)
                max_coords.z = max(max_coords.z, world_corner.z)
        
        current_size = max_coords - min_coords
        
        # Calculate scale factors for each dimension
        scale_factors = [1.0, 1.0, 1.0]
        if "width" in action:
            scale_factors[0] = action["width"] / current_size.x
        if "depth" in action:
            scale_factors[1] = action["depth"] / current_size.y
        if "height" in action:
            scale_factors[2] = action["height"] / current_size.z
        
        # Apply scaling around group center
        center = Vector((0, 0, 0))
        for obj in objects:
            center += obj.location
        center /= len(objects)
        
        scale_vec = Vector(scale_factors)
        for obj in objects:
            # Scale position relative to center
            offset = obj.location - center
            offset.x *= scale_factors[0]
            offset.y *= scale_factors[1]
            offset.z *= scale_factors[2]
            obj.location = center + offset
            
            # Scale object's scale
            obj.scale.x *= scale_factors[0]
            obj.scale.y *= scale_factors[1]
            obj.scale.z *= scale_factors[2]
        
        dims_str = ", ".join(f"{k}={v}" for k, v in action.items() if k in ("width", "depth", "height"))
        _log_diagnostic(f"Scaling asset '{group_name}' dimensions: {dims_str} (scale factors: {scale_factors})")
        
        return True, f"Set group '{group_name}' dimensions: {dims_str} (scaled by {scale_factors})"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_delete_group(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute delete_group action - deletes all objects in a group."""
    try:
        group_name = action["group_name"]
        objects = _get_group_objects(group_name)
        
        if not objects:
            return False, f"No objects found for group '{group_name}'"
        
        count = len(objects)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        
        bpy.ops.object.delete()
        
        _log_diagnostic(f"Deleted asset '{group_name}' with {count} components")
        
        return True, f"Deleted {count} objects from group '{group_name}'"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_parent_objects(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute parent_objects action - creates parent-child relationships."""
    try:
        parent_name = action["parent"]
        children_names = action["children"]
        
        parent_obj = bpy.data.objects.get(parent_name)
        if not parent_obj:
            return False, f"Parent object '{parent_name}' not found"
        
        child_objects = []
        missing_children = []
        for child_name in children_names:
            child_obj = bpy.data.objects.get(child_name)
            if not child_obj:
                missing_children.append(child_name)
            else:
                child_objects.append(child_obj)
        
        if missing_children:
            missing_str = ", ".join(missing_children)
            _log_diagnostic(f"Parenting failed - missing children: {missing_str}")
            return False, f"Child object(s) not found: {missing_str}"
        
        _log_diagnostic(f"Parenting {len(child_objects)} component(s) to '{parent_name}': {', '.join(children_names)}")
        
        # Set parent for each child (keep transform)
        for child_obj in child_objects:
            child_obj.parent = parent_obj
            child_obj.matrix_parent_inverse = parent_obj.matrix_world.inverted()
            _log_diagnostic(f"  Parented '{child_obj.name}' to '{parent_name}'")
        
        _log_diagnostic(f"Parented {len(child_objects)} component(s) to '{parent_name}'")
        
        return True, f"Parented {len(child_objects)} object(s) to '{parent_name}'"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


def _execute_unparent_objects(action: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute unparent_objects action - removes parent-child relationships."""
    try:
        children_names = action["children"]
        keep_transform = action.get("keep_transform", True)
        
        child_objects = []
        for child_name in children_names:
            child_obj = bpy.data.objects.get(child_name)
            if not child_obj:
                return False, f"Child object '{child_name}' not found"
            child_objects.append(child_obj)
        
        for child_obj in child_objects:
            if child_obj.parent:
                if keep_transform:
                    # Apply parent transform to child before unparenting
                    child_obj.matrix_world = child_obj.matrix_world
                child_obj.parent = None
        
        _log_diagnostic(f"Unparented {len(child_objects)} object(s)")
        
        return True, f"Unparented {len(child_objects)} object(s)"
    
    except RuntimeError as e:
        return False, f"Operation requires a valid Blender context: {e}"
    except Exception as e:
        return False, f"Execution failed: {e}"


# =============================================================================
# Multi-Action Support (V3)
# =============================================================================

def validate_actions(data: Dict[str, Any]) -> list:
    """
    Validate a multi-action response from the AI model.
    
    Args:
        data: Parsed JSON response, expected to have "actions" or "plan" key with list
        
    Returns:
        List of validated action dicts
        
    Raises:
        ValidationError: If response format is invalid or any action is invalid
    """
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    # Support both "actions" (V3) and "plan" (V5.2+) keys
    actions = data.get("actions") or data.get("plan")
    if not actions:
        raise ValidationError("Multi-action response requires 'actions' or 'plan' array")
    
    if not isinstance(actions, list):
        raise ValidationError("'actions'/'plan' must be an array")
    
    if len(actions) == 0:
        raise ValidationError("'actions'/'plan' array cannot be empty")
    
    validated_actions = []
    for i, action in enumerate(actions):
        try:
            validated = validate_action(action)
            validated_actions.append(validated)
        except ValidationError as e:
            raise ValidationError(f"Action {i+1}: {e}")
    
    return validated_actions


def execute_actions(actions: list) -> Tuple[bool, str]:
    """
    Execute multiple validated actions sequentially.
    
    Args:
        actions: List of validated action dicts
        
    Returns:
        (success: bool, message: str)
    """
    total = len(actions)
    for i, action in enumerate(actions):
        success, message = execute_action(action)
        if not success:
            return False, f"Action {i+1}/{total} failed: {message}"
    
    return True, f"Executed {total} action(s) successfully"