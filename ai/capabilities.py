# Blender AI Agent - High-Level Capability Layer
# Translates high-level actions into Blender 4.0.1 API calls

from typing import Dict, Any, Tuple, List, Optional

# Optional Blender imports - only available inside Blender
try:
    import bpy
    from mathutils import Vector
except ImportError:
    bpy = None
    Vector = None


# =============================================================================
# High-Level Light Capability
# =============================================================================

class LightCapability:
    """High-level light creation capability.
    
    Translates user-friendly parameters into Blender 4.0.1 API calls.
    """
    
    # Supported light types in Blender 4.0.1
    SUPPORTED_TYPES = {"POINT", "SUN", "SPOT", "AREA"}
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate create_light action parameters.
        
        Args:
            data: Raw action data from AI
            
        Returns:
            Validated action dict
            
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValueError("Response must be a JSON object")
        
        action = data.get("action")
        if action != "create_light":
            raise ValueError(f"Expected action 'create_light', got '{action}'")
        
        # Validate light_type
        light_type = data.get("light_type")
        if not light_type:
            raise ValueError("create_light requires 'light_type' field")
        if light_type not in {"POINT", "SUN", "SPOT", "AREA"}:
            raise ValueError(f"Unsupported light_type: {light_type}. Supported: POINT, SUN, SPOT, AREA")
        
        # Validate brightness (maps to energy)
        brightness = data.get("brightness")
        if brightness is None:
            raise ValueError("create_light requires 'brightness' field")
        if not isinstance(brightness, (int, float)):
            raise ValueError("'brightness' must be a number")
        if brightness < 0:
            raise ValueError("'brightness' must be >= 0")
        
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
        
        return {
            "action": "create_light",
            "light_type": validated["light_type"],
            "brightness": validated["brightness"],
            "color": validated["color"],
            "location": validated["location"],
            "rotation": validated["rotation"],
        }
    
    @staticmethod
    def execute(action: Dict[str, Any]) -> Tuple[bool, str]:
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
        # Optional Blender imports - only available inside Blender
        try:
            import bpy
        except ImportError:
            bpy = None
        
        if bpy is None:
            # Outside Blender - return success for testing
            return True, f"Created {action['light_type']} light with brightness {action['brightness']} at {action['location']} (test mode)"
        
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
            
            # Step 2: Configure light data (energy = brightness)
            light_obj.data.energy = action["brightness"]
            
            # Step 3: Set color
            light_obj.data.color = action["color"]
            
            # Note: rotation was already applied by light_add operator
            # No need to set rotation again
            
            return True, f"Created {action['light_type']} light with brightness {action['brightness']} at {action['location']}"
            
        except RuntimeError as e:
            return False, f"Operation requires a valid Blender context: {e}"
        except Exception as e:
            return False, f"Execution failed: {e}"


# =============================================================================
# Capability Registry
# =============================================================================

class CapabilityRegistry:
    """Registry of high-level capabilities.
    
    Maps high-level action names to capability handlers.
    """
    
    def __init__(self):
        self._capabilities = {}
        self._register_default_capabilities()
    
    def _register_default_capabilities(self):
        """Register built-in capabilities."""
        self.register("create_light", LightCapability())
    
    def register(self, action_name: str, capability):
        """Register a new capability."""
        self._capabilities[action_name] = capability
    
    def get(self, action_name: str):
        """Get capability by action name."""
        return self._capabilities.get(action_name)
    
    def is_supported(self, action_name: str) -> bool:
        """Check if action is a registered capability."""
        return action_name in self._capabilities
    
    def validate(self, action_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate action data using registered capability."""
        capability = self.get(action_name)
        if not capability:
            raise ValueError(f"Unsupported capability: {action_name}")
        return capability.validate(data)
    
    def execute(self, action: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute validated high-level action."""
        action_type = action.get("action")
        capability = self.get(action_type)
        if not capability:
            return False, f"Unknown capability: {action_type}"
        return capability.execute(action)


# Global registry instance
CAPABILITY_REGISTRY = CapabilityRegistry()