# Blender AI Agent - Action Validation & Execution
import bpy
from mathutils import Vector, Color
from typing import Dict, Any, Tuple, Optional
from ..utils import create_object_at_cursor


# Supported action types
SUPPORTED_ACTIONS = {
    "create_object", "delete_selected", "clear_scene",
    "move_object", "rotate_object", "scale_object",
    "create_material", "apply_material", "set_material_color"
}
SUPPORTED_OBJECT_TYPES = {"cube", "sphere", "cylinder"}

# Supported material types for V5.1
SUPPORTED_MATERIAL_TYPES = {"default", "wood", "metal", "plastic"}


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
    
    raise ValidationError(f"Unknown action: {action}")


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
    """Validate apply_material action."""
    material_name = data.get("material_name")
    if not material_name:
        raise ValidationError("apply_material requires 'material_name'")
    if not isinstance(material_name, str):
        raise ValidationError("'material_name' must be a string")
    
    object_target = data.get("object_target")
    if not object_target:
        raise ValidationError("apply_material requires 'object_target'")
    if object_target != "active":
        raise ValidationError("apply_material only supports object_target: 'active'")
    
    return {
        "action": "apply_material",
        "material_name": material_name,
        "object_target": "active",
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
    
    # Create object at specified location (not cursor)
    if obj_type == "cube":
        bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation, scale=scale)
    elif obj_type == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(location=location, rotation=rotation, scale=scale)
    elif obj_type == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(location=location, rotation=rotation, scale=scale)
    else:
        return False, f"Unknown object type: {obj_type}"
    
    obj = bpy.context.active_object
    if obj:
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
    """Execute apply_material action."""
    material_name = action["material_name"]
    
    obj, error = _get_active_object_or_error()
    if error:
        return False, error
    
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return False, f"Material '{material_name}' not found. Create it first."
    
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    
    return True, f"Applied material '{material_name}' to '{obj.name}'"


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


# =============================================================================
# Multi-Action Support (V3)
# =============================================================================

def validate_actions(data: Dict[str, Any]) -> list:
    """
    Validate a multi-action response from the AI model.
    
    Args:
        data: Parsed JSON response, expected to have "actions" key with list
        
    Returns:
        List of validated action dicts
        
    Raises:
        ValidationError: If response format is invalid or any action is invalid
    """
    if not isinstance(data, dict):
        raise ValidationError("Response must be a JSON object")
    
    actions = data.get("actions")
    if not actions:
        raise ValidationError("Multi-action response requires 'actions' array")
    
    if not isinstance(actions, list):
        raise ValidationError("'actions' must be an array")
    
    if len(actions) == 0:
        raise ValidationError("'actions' array cannot be empty")
    
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