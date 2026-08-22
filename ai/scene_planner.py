# Blender AI Agent - Scene Planner / Scene Composer
# High-level scene plan validation and execution

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from typing import Literal

from .actions import (
    validate_action,
    execute_action,
    validate_actions,
    execute_actions,
    ValidationError,
    SUPPORTED_ACTIONS,
)
from .capabilities import CAPABILITY_REGISTRY


# =============================================================================
# Scene Plan Data Structures
# =============================================================================

@dataclass
class ScenePlan:
    """A validated scene plan ready for execution."""
    name: str = "Unnamed Scene"
    description: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)
    max_actions: int = 20

    def __post_init__(self):
        if len(self.actions) > self.max_actions:
            raise ValueError(f"Scene plan exceeds maximum of {self.max_actions} actions")


@dataclass
class SceneExecutionResult:
    """Result of scene plan execution."""
    success: bool
    completed_actions: int
    failed_actions: int
    total_actions: int
    message: str
    action_results: List[Dict[str, Any]] = field(default_factory=list)


# =============================================================================
# Scene Plan Validation
# =============================================================================

def validate_scene_plan_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Centralized validation for a complete scene plan dict.
    
    This is the SINGLE validation gate that must pass before ANY Blender action executes.
    Validates the complete raw dict structure, all actions, and all parameters.
    
    Args:
        data: Raw parsed JSON response from AI
        
    Returns:
        Validated dict with all actions validated
        
    Raises:
        ValidationError: If any part of the plan is invalid
    """
    if not isinstance(data, dict):
        raise ValidationError("Scene plan must be a JSON object")
    
    # Validate scene metadata
    scene_data = data.get("scene")
    if scene_data is None:
        raise ValidationError("Scene plan requires 'scene' object")
    if not isinstance(scene_data, dict):
        raise ValidationError("'scene' must be an object")
    
    name = scene_data.get("name", "Unnamed Scene")
    if not isinstance(name, str):
        raise ValidationError("'scene.name' must be a string")
    
    description = scene_data.get("description", "")
    if not isinstance(description, str):
        raise ValidationError("'scene.description' must be a string")
    
    # Validate actions array
    actions = data.get("actions")
    if actions is None:
        raise ValidationError("Scene plan requires 'actions' array")
    
    if not isinstance(actions, list):
        raise ValidationError("'actions' must be an array")
    
    if len(actions) == 0:
        raise ValidationError("'actions' array cannot be empty")
    
    if len(actions) > 20:
        raise ValidationError("Scene plan exceeds maximum of 20 actions")
    
    # Validate each action using existing validation
    validated_actions = []
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValidationError(f"Action {i+1}: must be an object")
        
        try:
            validated = validate_action(action)
            validated_actions.append(validated)
        except Exception as e:
            raise ValidationError(f"Action {i+1}: {e}")
    
    # Return validated dict ready for execution
    return {
        "scene": {
            "name": name,
            "description": description
        },
        "actions": validated_actions
    }


def validate_scene_plan(data: Dict[str, Any]) -> ScenePlan:
    """
    Validate a scene plan from AI response.
    
    Expected format:
    {
        "scene": {
            "name": "Sunset Environment",
            "description": "A peaceful sunset over water"
        },
        "actions": [
            {"action": "create_light", "light_type": "SUN", ...},
            {"action": "create_object", "object_type": "plane", ...},
            ...
        ]
    }
    
    Returns:
        Validated ScenePlan object
        
    Raises:
        ValidationError: If the plan is invalid
    """
    validated_dict = validate_scene_plan_dict(data)
    
    return ScenePlan(
        name=validated_dict["scene"]["name"],
        description=validated_dict["scene"]["description"],
        actions=validated_dict["actions"]
    )
    """
    Validate a scene plan from AI response.
    
    Expected format:
    {
        "scene": {
            "name": "Sunset Environment",
            "description": "A peaceful sunset over water"
        },
        "actions": [
            {"action": "create_light", "light_type": "SUN", ...},
            {"action": "create_object", "object_type": "plane", ...},
            ...
        ]
    }
    
    Returns:
        Validated ScenePlan object
        
    Raises:
        ValidationError: If the plan is invalid
    """
    if not isinstance(data, dict):
        raise ValidationError("Scene plan must be a JSON object")
    
    # Extract scene metadata
    scene_data = data.get("scene", {})
    if not isinstance(scene_data, dict):
        raise ValidationError("'scene' must be an object")
    
    name = scene_data.get("name", "Unnamed Scene")
    if not isinstance(name, str):
        raise ValidationError("'scene.name' must be a string")
    
    description = scene_data.get("description", "")
    if not isinstance(description, str):
        raise ValidationError("'scene.description' must be a string")
    
    # Extract actions
    actions = data.get("actions")
    if actions is None:
        raise ValidationError("Scene plan requires 'actions' array")
    
    if not isinstance(actions, list):
        raise ValidationError("'actions' must be an array")
    
    if len(actions) == 0:
        raise ValidationError("'actions' array cannot be empty")
    
    if len(actions) > 20:
        raise ValidationError("Scene plan exceeds maximum of 20 actions")
    
    # Validate each action using existing validation
    validated_actions = []
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValidationError(f"Action {i+1}: must be an object")
        
        try:
            validated = validate_action(action)
            validated_actions.append(validated)
        except Exception as e:
            raise ValidationError(f"Action {i+1}: {e}")
    
    return ScenePlan(
        name=name,
        description=description,
        actions=validated
    )


# =============================================================================
# Scene Plan Execution
# =============================================================================

def execute_scene_plan(plan: ScenePlan) -> Dict[str, Any]:
    """
    Execute a validated scene plan.
    
    Returns execution result with:
    - success: overall success/failure
    - completed_actions: number of successful actions
    - failed_actions: number of failed actions
    - total_actions: total actions in plan
    - message: summary message
    - action_results: detailed results for each action
    """
    results = []
    completed = 0
    failed = 0
    
    for i, action in enumerate(plan.actions):
        action_type = action.get("action", "unknown")
        try:
            success, message = execute_action(action)
            result = {
                "step": i + 1,
                "action": action_type,
                "success": success,
                "message": message
            }
            results.append(result)
            
            if success:
                completed += 1
            else:
                failed += 1
                # Stop on first failure (could be configurable later)
                break
        except Exception as e:
            result = {
                "step": i + 1,
                "action": action_type,
                "success": False,
                "message": f"Execution error: {e}"
            }
            results.append(result)
            failed += 1
            break
    
    total = len(plan.actions)
    success = failed == 0
    
    if success:
        message = f"Scene '{plan.name}' created successfully ({completed}/{total} actions)"
    else:
        message = f"Scene '{plan.name}' failed at step {completed + 1}: {results[-1]['message'] if results else 'Unknown error'}"
    
    return {
        "success": success,
        "completed_actions": completed,
        "failed_actions": failed,
        "total_actions": total,
        "message": message,
        "action_results": results
    }


# =============================================================================
# High-Level Capability: Scene Plan Execution
# =============================================================================

class ScenePlanCapability:
    """High-level capability to execute a complete scene plan."""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a scene plan action."""
        if not isinstance(data, dict):
            raise ValueError("Scene plan must be a JSON object")
        
        action = data.get("action")
        if action != "execute_scene_plan":
            raise ValueError(f"Expected action 'execute_scene_plan', got '{data.get('action')}'")
        
        plan_data = data.get("plan")
        if plan_data is None:
            raise ValueError("execute_scene_plan requires 'plan' object")
        
        # Validate the plan structure
        plan = validate_scene_plan(plan_data)
        
        return {
            "action": "execute_scene_plan",
            "plan": {
                "name": plan.name,
                "description": plan.description,
                "actions": plan.actions
            }
        }
    
    @staticmethod
    def execute(action: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute a scene plan."""
        plan_data = action.get("plan")
        if not plan_data:
            return False, "Missing plan data"
        
        try:
            plan = validate_scene_plan(plan_data)
            result = execute_scene_plan(plan)
            
            message = result["message"]
            if not result["success"]:
                return False, message
            
            return True, message
        except ValidationError as e:
            return False, f"Invalid scene plan: {e}"
        except Exception as e:
            return False, f"Scene execution failed: {e}"


# Register the scene plan capability
CAPABILITY_REGISTRY.register("execute_scene_plan", ScenePlanCapability())


# =============================================================================
# Convenience Functions for AI Integration
# =============================================================================

def parse_and_execute_scene(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and execute a scene plan from AI response.
    
    Handles both 'actions' and 'plan' formats for backward compatibility.
    """
    if not isinstance(data, dict):
        return {
            "success": False,
            "completed_actions": 0,
            "failed_actions": 1,
            "total_actions": 0,
            "message": "Invalid response format",
            "action_results": []
        }
    
    # Check for scene plan format
    if "plan" in data:
        try:
            plan = validate_scene_plan(data["plan"])
            return execute_scene_plan(plan)
        except ValidationError as e:
            return {
                "success": False,
                "completed_actions": 0,
                "failed_actions": 1,
                "total_actions": 0,
                "message": f"Invalid scene plan: {e}",
                "action_results": []
            }
    
    # Fallback to existing multi-action format
    if "actions" in data:
        try:
            validated_actions = validate_actions(data)
            success, message = execute_actions(validated_actions)
            return {
                "success": success,
                "completed_actions": len(validated_actions) if success else 0,
                "failed_actions": 0 if success else 1,
                "total_actions": len(validated_actions),
                "message": message,
                "action_results": []
            }
        except ValidationError as e:
            return {
                "success": False,
                "completed_actions": 0,
                "failed_actions": 1,
                "total_actions": 0,
                "message": f"Invalid actions: {e}",
                "action_results": []
            }
    
    return {
        "success": False,
        "completed_actions": 0,
        "failed_actions": 1,
        "total_actions": 0,
        "message": "Response must contain 'plan' or 'actions'",
        "action_results": []
    }