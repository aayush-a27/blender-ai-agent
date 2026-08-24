# Blender AI Agent - Generic Operation Registry
# Whitelisted Blender operations for V5.2.1+

from typing import Dict, Any, Optional, List, Callable


class OperationSchema:
    """Schema definition for a whitelisted Blender operation."""
    
    def __init__(
        self,
        operator: str,
        description: str,
        params: Dict[str, Dict[str, Any]],
        required_params: List[str] = None,
    ):
        self.operator = operator
        self.description = description
        self.params = params  # param_name -> {type, default, description, enum}
        self.required_params = required_params or []
    
    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize parameters for this operation."""
        if not isinstance(params, dict):
            raise ValueError(f"Parameters must be an object, got {type(params).__name__}")
        
        validated = {}
        # Check required parameters
        for req in self.required_params:
            if req not in params:
                raise ValueError(f"Missing required parameter: {req}")
        
        # Validate each provided parameter
        for key, value in params.items():
            if key not in self.params:
                raise ValueError(f"Unsupported parameter '{key}' for operation. Allowed: {list(self.params.keys())}")
            
            param_schema = self.params[key]
            validated[key] = self._validate_param_value(key, value, param_schema)
        
        # Apply defaults for missing optional parameters
        for key, schema in self.params.items():
            if key not in validated and "default" in schema:
                validated[key] = schema["default"]
        
        return validated
    
    def _validate_param_value(self, key: str, value: Any, schema: Dict[str, Any]) -> Any:
        """Validate a single parameter value against its schema."""
        expected_type = schema.get("type")
        
        if expected_type == "number":
            if not isinstance(value, (int, float)):
                raise ValueError(f"Parameter '{key}' must be a number")
            # Check bounds if specified
            if "min" in schema and value < schema["min"]:
                raise ValueError(f"Parameter '{key}' must be >= {schema['min']}")
            if "max" in schema and value > schema["max"]:
                raise ValueError(f"Parameter '{key}' must be <= {schema['max']}")
            return float(value)
        
        elif expected_type == "integer":
            if not isinstance(value, int):
                raise ValueError(f"Parameter '{key}' must be an integer")
            if "min" in schema and value < schema["min"]:
                raise ValueError(f"Parameter '{key}' must be >= {schema['min']}")
            if "max" in schema and value > schema["max"]:
                raise ValueError(f"Parameter '{key}' must be <= {schema['max']}")
            return value
        
        elif expected_type == "string":
            if not isinstance(value, str):
                raise ValueError(f"Parameter '{key}' must be a string")
            if "enum" in schema and value not in schema["enum"]:
                raise ValueError(f"Parameter '{key}' must be one of: {schema['enum']}")
            return value
        
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                raise ValueError(f"Parameter '{key}' must be a boolean")
            return value
        
        elif expected_type == "array":
            if not isinstance(value, (list, tuple)):
                raise ValueError(f"Parameter '{key}' must be an array")
            if "items" in schema:
                # Validate array items
                item_schema = schema["items"]
                return [self._validate_param_value(f"{key}[{i}]", v, item_schema) for i, v in enumerate(value)]
            return list(value)
        
        else:
            # Unknown type - pass through
            return value


# Registry of whitelisted Blender operations
# Only safe, commonly used operations are included initially
BLENDER_OPERATIONS = {
    "object.light_add": OperationSchema(
        operator="object.light_add",
        description="Add a light object to the scene",
        params={
            "type": {"type": "string", "enum": ["POINT", "SUN", "SPOT", "AREA"], "default": "POINT", "description": "Type of light"},
            "radius": {"type": "number", "default": 1.0, "min": 0.01, "description": "Light radius"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
            "scale": {"type": "array", "items": {"type": "number"}, "default": [1.0, 1.0, 1.0], "description": "Scale [x, y, z]"},
            "energy": {"type": "number", "default": 10.0, "min": 0.0, "description": "Light energy/intensity"},
            "color": {"type": "array", "items": {"type": "number"}, "default": [1.0, 1.0, 1.0], "description": "Light color [r, g, b] 0-1"},
        },
        required_params=[],
    ),
    
    "object.camera_add": OperationSchema(
        operator="object.camera_add",
        description="Add a camera to the scene",
        params={
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
        },
        required_params=[],
    ),
    
    "object.empty_add": OperationSchema(
        operator="object.empty_add",
        description="Add an empty object (useful as parent/target)",
        params={
            "type": {"type": "string", "enum": ["PLAIN_AXES", "ARROWS", "SINGLE_ARROW", "CIRCLE", "CUBE", "SPHERE", "CONE"], "default": "PLAIN_AXES", "description": "Empty display type"},
            "radius": {"type": "number", "default": 1.0, "min": 0.01, "description": "Empty display size"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
        },
        required_params=[],
    ),
    
    "mesh.primitive_plane_add": OperationSchema(
        operator="mesh.primitive_plane_add",
        description="Add a plane mesh",
        params={
            "size": {"type": "number", "default": 2.0, "min": 0.01, "description": "Plane size"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
        },
        required_params=[],
    ),
    
    "object.delete": OperationSchema(
        operator="object.delete",
        description="Delete the active object or selected objects",
        params={
            "use_global": {"type": "boolean", "default": False, "description": "Delete from all scenes"},
            "confirm": {"type": "boolean", "default": False, "description": "Confirm deletion"},
        },
        required_params=[],
    ),
    
    "object.select_all": OperationSchema(
        operator="object.select_all",
        description="Select or deselect all objects",
        params={
            "action": {"type": "string", "enum": ["SELECT", "DESELECT", "INVERT", "TOGGLE"], "default": "SELECT", "description": "Selection action"},
        },
        required_params=[],
    ),
    
    "object.shade_smooth": OperationSchema(
        operator="object.shade_smooth",
        description="Apply smooth shading to selected objects",
        params={},
        required_params=[],
    ),
    
    "object.shade_flat": OperationSchema(
        operator="object.shade_flat",
        description="Apply flat shading to selected objects",
        params={},
        required_params=[],
    ),
    
    # V5.2.2 - Object Creation
    "mesh.primitive_cube_add": OperationSchema(
        operator="mesh.primitive_cube_add",
        description="Add a cube mesh",
        params={
            "size": {"type": "number", "default": 2.0, "min": 0.01, "description": "Cube size"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
            "scale": {"type": "array", "items": {"type": "number"}, "default": [1.0, 1.0, 1.0], "description": "Scale [x, y, z]"},
        },
        required_params=[],
    ),
    
    "mesh.primitive_uv_sphere_add": OperationSchema(
        operator="mesh.primitive_uv_sphere_add",
        description="Add a UV sphere mesh",
        params={
            "radius": {"type": "number", "default": 1.0, "min": 0.01, "description": "Sphere radius"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
            "scale": {"type": "array", "items": {"type": "number"}, "default": [1.0, 1.0, 1.0], "description": "Scale [x, y, z]"},
        },
        required_params=[],
    ),
    
    "mesh.primitive_cylinder_add": OperationSchema(
        operator="mesh.primitive_cylinder_add",
        description="Add a cylinder mesh",
        params={
            "radius": {"type": "number", "default": 1.0, "min": 0.01, "description": "Cylinder radius"},
            "depth": {"type": "number", "default": 2.0, "min": 0.01, "description": "Cylinder depth/height"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
            "scale": {"type": "array", "items": {"type": "number"}, "default": [1.0, 1.0, 1.0], "description": "Scale [x, y, z]"},
        },
        required_params=[],
    ),
    
    "mesh.primitive_cone_add": OperationSchema(
        operator="mesh.primitive_cone_add",
        description="Add a cone mesh",
        params={
            "radius1": {"type": "number", "default": 1.0, "min": 0.01, "description": "Base radius"},
            "radius2": {"type": "number", "default": 0.0, "min": 0.0, "description": "Top radius (0 for point)"},
            "depth": {"type": "number", "default": 2.0, "min": 0.01, "description": "Cone height"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
            "scale": {"type": "array", "items": {"type": "number"}, "default": [1.0, 1.0, 1.0], "description": "Scale [x, y, z]"},
        },
        required_params=[],
    ),
    
    "mesh.primitive_torus_add": OperationSchema(
        operator="mesh.primitive_torus_add",
        description="Add a torus mesh",
        params={
            "major_radius": {"type": "number", "default": 1.0, "min": 0.01, "description": "Major radius (from center to tube center)"},
            "minor_radius": {"type": "number", "default": 0.25, "min": 0.01, "description": "Minor radius (tube radius)"},
            "major_segments": {"type": "integer", "default": 48, "min": 3, "description": "Number of segments for the major radius"},
            "minor_segments": {"type": "integer", "default": 16, "min": 3, "description": "Number of segments for the minor radius"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
        },
        required_params=[],
    ),
    
    "mesh.primitive_plane_add": OperationSchema(
        operator="mesh.primitive_plane_add",
        description="Add a plane mesh",
        params={
            "size": {"type": "number", "default": 2.0, "min": 0.01, "description": "Plane size"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
        },
        required_params=[],
    ),
    
    # V5.2.2 - Lighting
    "object.light_add": OperationSchema(
        operator="object.light_add",
        description="Add a light object to the scene",
        params={
            "type": {"type": "string", "enum": ["POINT", "SUN", "SPOT", "AREA"], "default": "POINT", "description": "Type of light"},
            "radius": {"type": "number", "default": 1.0, "min": 0.01, "description": "Light radius"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
            "scale": {"type": "array", "items": {"type": "number"}, "default": [1.0, 1.0, 1.0], "description": "Scale [x, y, z]"},
            "energy": {"type": "number", "default": 10.0, "min": 0.0, "description": "Light energy/intensity"},
            "color": {"type": "array", "items": {"type": "number"}, "default": [1.0, 1.0, 1.0], "description": "Light color [r, g, b] 0-1"},
        },
        required_params=[],
    ),
    
    # V5.2.2 - Camera
    "object.camera_add": OperationSchema(
        operator="object.camera_add",
        description="Add a camera to the scene",
        params={
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
        },
        required_params=[],
    ),
    
    # V5.2.2 - Object Transforms
    "object.select_all": OperationSchema(
        operator="object.select_all",
        description="Select or deselect all objects",
        params={
            "action": {"type": "string", "enum": ["SELECT", "DESELECT", "INVERT", "TOGGLE"], "default": "SELECT", "description": "Selection action"},
        },
        required_params=[],
    ),
    
    "object.shade_smooth": OperationSchema(
        operator="object.shade_smooth",
        description="Apply smooth shading to selected objects",
        params={},
        required_params=[],
    ),
    
    "object.shade_flat": OperationSchema(
        operator="object.shade_flat",
        description="Apply flat shading to selected objects",
        params={},
        required_params=[],
    ),
    
    # V5.2.2 - Empty
    "object.empty_add": OperationSchema(
        operator="object.empty_add",
        description="Add an empty object (useful as parent/target)",
        params={
            "type": {"type": "string", "enum": ["PLAIN_AXES", "ARROWS", "SINGLE_ARROW", "CIRCLE", "CUBE", "SPHERE", "CONE"], "default": "PLAIN_AXES", "description": "Empty display type"},
            "radius": {"type": "number", "default": 1.0, "min": 0.01, "description": "Empty display size"},
            "location": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Location [x, y, z]"},
            "rotation": {"type": "array", "items": {"type": "number"}, "default": [0.0, 0.0, 0.0], "description": "Rotation in radians [x, y, z]"},
        },
        required_params=[],
    ),

    # V5.4 - Linear Duplication
    "object.duplicate_linear": OperationSchema(
        operator="object.duplicate_linear",
        description="Create linear duplicates of an object along an axis",
        params={
            "source": {"type": "string", "description": "Name of the source object to duplicate"},
            "count": {"type": "integer", "default": 5, "min": 2, "max": 100, "description": "Number of total objects (including original if keep_original)"},
            "axis": {"type": "string", "enum": ["X", "Y", "Z"], "default": "Z", "description": "Axis for linear distribution"},
            "spacing": {"type": "number", "default": 1.0, "min": 0.001, "description": "Distance between duplicates along the axis"},
            "start_offset_x": {"type": "number", "default": 0.0, "description": "X offset for the first duplicate relative to source"},
            "start_offset_y": {"type": "number", "default": 0.0, "description": "Y offset for the first duplicate relative to source"},
            "start_offset_z": {"type": "number", "default": 0.0, "description": "Z offset for the first duplicate relative to source"},
            "keep_original": {"type": "boolean", "default": True, "description": "Whether to keep the source object"},
        },
        required_params=["source"],
    ),

    # V5.5 - Mirror/Symmetry
    "object.mirror_object": OperationSchema(
        operator="object.mirror_object",
        description="Create a mirrored copy of an object across a plane",
        params={
            "source": {"type": "string", "description": "Name of the source object to mirror"},
            "plane": {"type": "string", "enum": ["XY", "YZ", "XZ"], "default": "YZ", "description": "Mirror plane (XY, YZ, or XZ)"},
            "offset": {"type": "number", "default": 0.0, "description": "Plane offset from origin along the normal axis"},
            "merge": {"type": "boolean", "default": False, "description": "Whether to merge the mirrored object with the source (for closed meshes)"},
            "keep_original": {"type": "boolean", "default": True, "description": "Whether to keep the source object"},
        },
        required_params=["source"],
    ),

    # V5.7 - Object Alignment
    "object.align_objects": OperationSchema(
        operator="object.align_objects",
        description="Align source object relative to target object using world-space bounding boxes",
        params={
            "source": {"type": "string", "description": "Name of the source object to align"},
            "target": {"type": "string", "description": "Name of the target object to align to"},
            "axis": {"type": "string", "enum": ["X", "Y", "Z"], "default": "Z", "description": "Axis along which to align"},
            "mode": {"type": "string", "enum": ["MIN", "CENTER", "MAX"], "default": "CENTER", "description": "Alignment mode: MIN (min bounds), CENTER (centers), MAX (max bounds)"},
        },
        required_params=["source", "target"],
    ),

    # V5.7 - Object Contact Placement
    "object.place_on": OperationSchema(
        operator="object.place_on",
        description="Place source object against target object using world-space bounding boxes",
        params={
            "source": {"type": "string", "description": "Name of the source object to place"},
            "target": {"type": "string", "description": "Name of the target object to place against"},
            "axis": {"type": "string", "enum": ["X", "Y", "Z"], "default": "Z", "description": "Axis along which to place (Z=on top, X=against X, Y=against Y)"},
            "offset": {"type": "number", "default": 0.0, "description": "Additional offset from contact point"},
        },
        required_params=["source", "target"],
    ),

    # V5.8 - Bevel/Chamfer
    "object.apply_bevel": OperationSchema(
        operator="object.apply_bevel",
        description="Apply a bevel modifier to a mesh object for rounded/chamfered edges",
        params={
            "source": {"type": "string", "description": "Name of the source object to bevel"},
            "width": {"type": "number", "default": 0.05, "min": 0.001, "description": "Bevel width (distance from original edge)"},
            "segments": {"type": "integer", "default": 3, "min": 1, "max": 64, "description": "Number of bevel segments (higher = smoother)"},
            "limit_method": {"type": "string", "enum": ["ANGLE", "WEIGHT", "VGROUP", "NONE"], "default": "ANGLE", "description": "How to limit bevel application"},
            "angle_limit": {"type": "number", "default": 0.523599, "min": 0.0, "max": 3.14159, "description": "Angle limit for ANGLE limit method (radians)"},
            "affect": {"type": "string", "enum": ["EDGES", "VERTICES"], "default": "EDGES", "description": "What to bevel: edges or vertices"},
        },
        required_params=["source"],
    ),
}


def get_operation(operator: str) -> Optional[OperationSchema]:
    """Get operation schema by operator name."""
    return BLENDER_OPERATIONS.get(operator)


def is_whitelisted(operator: str) -> bool:
    """Check if an operator is whitelisted."""
    return operator in BLENDER_OPERATIONS


def list_whitelisted_operators() -> List[str]:
    """Get list of all whitelisted operator names."""
    return list(BLENDER_OPERATIONS.keys())


def validate_bpy_operation(operator: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a bpy_op action.
    
    Returns:
        Validated action dict with operator and sanitized params.
        
    Raises:
        ValueError: If operator not whitelisted or params invalid.
    """
    if not isinstance(operator, str):
        raise ValueError("Operator must be a string")
    
    schema = get_operation(operator)
    if schema is None:
        raise ValueError(f"Unsupported Blender operation: {operator}. Whitelisted: {list_whitelisted_operators()}")
    
    validated_params = schema.validate_params(params or {})
    
    return {
        "action": "bpy_op",
        "operator": operator,
        "params": validated_params,
    }