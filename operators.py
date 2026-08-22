import bpy
import os
from bpy.types import Operator
from .ai.client import send_command, NVIDIAAPIError
from .ai.actions import validate_action, execute_action, validate_actions, execute_actions, ValidationError


class OBJECT_OT_create_cube(Operator):
    bl_idname = "object.create_cube"
    bl_label = "Create Cube"
    bl_description = "Create a cube at the cursor location"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.primitive_cube_add()
        self.report({'INFO'}, "Cube created")
        return {'FINISHED'}


class OBJECT_OT_create_sphere(Operator):
    bl_idname = "object.create_sphere"
    bl_label = "Create Sphere"
    bl_description = "Create a UV sphere at the cursor location"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.primitive_uv_sphere_add()
        self.report({'INFO'}, "Sphere created")
        return {'FINISHED'}


class OBJECT_OT_create_cylinder(Operator):
    bl_idname = "object.create_cylinder"
    bl_label = "Create Cylinder"
    bl_description = "Create a cylinder at the cursor location"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.primitive_cylinder_add()
        self.report({'INFO'}, "Cylinder created")
        return {'FINISHED'}


class OBJECT_OT_delete_selected(Operator):
    bl_idname = "object.delete_selected"
    bl_label = "Delete Selected"
    bl_description = "Delete all selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None and len(context.selected_objects) > 0

    def execute(self, context):
        count = len(context.selected_objects)
        bpy.ops.object.delete()
        self.report({'INFO'}, f"Deleted {count} object(s)")
        return {'FINISHED'}


class OBJECT_OT_clear_scene(Operator):
    bl_idname = "object.clear_scene"
    bl_label = "Clear Scene"
    bl_description = "Delete all objects in the scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        self.report({'INFO'}, "Scene cleared")
        return {'FINISHED'}


class BLENDER_AI_AGENT_OT_test_connection(Operator):
    bl_idname = "blender_ai_agent.test_connection"
    bl_label = "Test NVIDIA Nemotron Connection"
    bl_description = "Verify API key, endpoint, and model connectivity"
    bl_options = {'REGISTER'}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences

        if not prefs.api_key and not os.environ.get("NVIDIA_API_KEY"):
            self.report({'ERROR'}, "API key not configured")
            return {'CANCELLED'}

        try:
            # Send a minimal test command
            from .ai.client import send_command, NVIDIAAPIError
            response = send_command("Test connection", prefs)
            
            # Just verify we got a valid JSON response structure
            if isinstance(response, dict) and "action" in response:
                self.report({'INFO'}, "NVIDIA Nemotron connection successful")
            else:
                self.report({'WARNING'}, "Connected but unexpected response format")
                
        except NVIDIAAPIError as e:
            if e.status_code == 401:
                self.report({'ERROR'}, "Authentication failed: Invalid API key")
            elif e.status_code == 404:
                self.report({'ERROR'}, "Model not found: Check model name and endpoint")
            elif e.status_code and 500 <= e.status_code < 600:
                self.report({'ERROR'}, f"Server error (HTTP {e.status_code})")
            else:
                self.report({'ERROR'}, f"Connection failed: {e.message}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Unexpected error: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


class OBJECT_OT_execute_scene_plan(Operator):
    bl_idname = "blender_ai_agent.execute_scene_plan"
    bl_label = "Execute Scene Plan"
    bl_description = "Execute a structured scene plan with multiple actions"
    bl_options = {'REGISTER', 'UNDO'}

    plan_data: bpy.props.StringProperty(
        name="Scene Plan Data",
        description="JSON string containing the scene plan",
        default="",
    )

    def execute(self, context):
        if not self.plan_data.strip():
            self.report({'WARNING'}, "Empty scene plan")
            return {'CANCELLED'}

        try:
            import json
            plan_data = json.loads(self.plan_data)
            
            from .ai.scene_planner import parse_and_execute_scene
            result = parse_and_execute_scene(plan_data)
            
            if result["success"]:
                self.report({'INFO'}, result["message"])
            else:
                self.report({'ERROR'}, result["message"])
                return {'CANCELLED'}
                
        except json.JSONDecodeError:
            self.report({'ERROR'}, "Invalid JSON in scene plan")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Scene plan execution failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


class OBJECT_OT_ai_command(Operator):
    bl_idname = "object.ai_command"
    bl_label = "Execute AI Command"
    bl_description = "Send natural language command to NVIDIA Nemotron and execute the result"
    bl_options = {'REGISTER', 'UNDO'}

    command: bpy.props.StringProperty(
        name="Command",
        description="Natural language command to send to AI",
        default="",
    )

    def execute(self, context):
        props = context.scene.blender_ai_agent
        prefs = context.preferences.addons[__package__].preferences

        user_command = self.command or props.ai_command
        if not user_command.strip():
            self.report({'WARNING'}, "Empty command")
            return {'CANCELLED'}

        # Update status: Sending
        props.ai_status = 'SENDING'
        props.ai_error_message = ""

        try:
            # Collect scene context for context-aware planning
            from .ai.scene_context import collect_scene_context
            scene_context = collect_scene_context()
            
            # Send to NVIDIA API
            props.ai_status = 'PROCESSING'
            response = send_command(user_command, prefs, scene_context=scene_context)
            
            # Validate response - detect format
            props.ai_status = 'EXECUTING'
            
            if isinstance(response, dict):
                # Scene plan format (V5.3+): {"scene": {...}, "actions": [...]} - MUST CHECK FIRST
                if "scene" in response and "actions" in response:
                    from .ai.scene_planner import parse_and_execute_scene
                    result = parse_and_execute_scene(response)
                    success = result["success"]
                    message = result["message"]
                elif "actions" in response:
                    # Multi-action format (V3): {"actions": [...]}
                    validated_actions = validate_actions(response)
                    success, message = execute_actions(validated_actions)
                elif "plan" in response:
                    # Plan format (V5.2+): {"plan": [...]}
                    validated_actions = validate_actions(response)
                    success, message = execute_actions(validated_actions)
                else:
                    # Single-action format (backward compatible): {"action": "..."}
                    validated_action = validate_action(response)
                    success, message = execute_action(validated_action)
            else:
                # Single-action format (backward compatible): {"action": "..."}
                validated_action = validate_action(response)
                success, message = execute_action(validated_action)
            
            # Execute in Blender
            if success:
                props.ai_status = 'COMPLETED'
                self.report({'INFO'}, message)
            else:
                props.ai_status = 'ERROR'
                props.ai_error_message = message
                self.report({'ERROR'}, message)
                return {'CANCELLED'}

        except NVIDIAAPIError as e:
            props.ai_status = 'ERROR'
            props.ai_error_message = str(e)
            self.report({'ERROR'}, f"AI Error: {e.message}")
            return {'CANCELLED'}
        except ValidationError as e:
            props.ai_status = 'ERROR'
            props.ai_error_message = f"Invalid AI response: {e}"
            self.report({'ERROR'}, f"Invalid AI response: {e}")
            return {'CANCELLED'}
        except Exception as e:
            props.ai_status = 'ERROR'
            props.ai_error_message = f"Unexpected error: {e}"
            self.report({'ERROR'}, f"Error: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


classes = (
    OBJECT_OT_create_cube,
    OBJECT_OT_create_sphere,
    OBJECT_OT_create_cylinder,
    OBJECT_OT_delete_selected,
    OBJECT_OT_clear_scene,
    OBJECT_OT_ai_command,
    OBJECT_OT_execute_scene_plan,
    BLENDER_AI_AGENT_OT_test_connection,
)


def _unregister_class_safe(cls):
    """Unregister class if it's currently registered. Safe to call multiple times."""
    try:
        bpy.utils.unregister_class(cls)
    except RuntimeError:
        pass  # Class wasn't registered


def register():
    # Ensure clean state (handles Blender reload where unregister may not have run)
    for cls in reversed(classes):
        _unregister_class_safe(cls)

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        _unregister_class_safe(cls)