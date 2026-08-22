import bpy
import os
from bpy.types import Operator
from mathutils import Vector, Matrix
from math import radians, sin, cos
from .ai.client import send_command, NVIDIAAPIError
from .ai.actions import validate_action, execute_action, validate_actions, execute_actions, ValidationError


class BLENDER_AI_AGENT_OT_edit_command(Operator):
    """Open the Text Editor with the AI command datablock for multiline editing."""
    bl_idname = "blender_ai_agent.edit_command"
    bl_label = "Edit Command"
    bl_description = "Open Text Editor to write/paste multiline AI command"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.blender_ai_agent
        text_block_name = props.ai_command_text_block or "BlenderAICommand"
        text_block = bpy.data.texts.get(text_block_name)
        if text_block is None:
            text_block = bpy.data.texts.new(name=text_block_name)
            props.ai_command_text_block = text_block_name

        # 1. Try to find an existing TEXT_EDITOR area and use it
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'TEXT_EDITOR':
                    area.spaces.active.text = text_block
                    return {'FINISHED'}

        # 2. No Text Editor exists - convert current area to TEXT_EDITOR directly
        area = context.area
        if area:
            area.type = 'TEXT_EDITOR'
            area.spaces.active.text = text_block

        return {'FINISHED'}


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


class OBJECT_OT_duplicate_radial(Operator):
    """Duplicate an object radially around a center point."""
    bl_idname = "object.duplicate_radial"
    bl_label = "Duplicate Radial"
    bl_description = "Create radial duplicates of an object around a center point"
    bl_options = {'REGISTER', 'UNDO'}

    source: bpy.props.StringProperty(
        name="Source Object",
        description="Name of the source object to duplicate",
        default="",
    )

    count: bpy.props.IntProperty(
        name="Count",
        description="Number of duplicates to create (including original if keep_original)",
        default=5,
        min=2,
        max=32,
    )

    center_x: bpy.props.FloatProperty(
        name="Center X",
        description="X coordinate of radial center",
        default=0.0,
    )

    center_y: bpy.props.FloatProperty(
        name="Center Y",
        description="Y coordinate of radial center",
        default=0.0,
    )

    center_z: bpy.props.FloatProperty(
        name="Center Z",
        description="Z coordinate of radial center",
        default=0.0,
    )

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Rotation axis for radial distribution",
        items=[
            ('X', "X", "Rotate around X axis"),
            ('Y', "Y", "Rotate around Y axis"),
            ('Z', "Z", "Rotate around Z axis"),
        ],
        default='Z',
    )

    angle_offset: bpy.props.FloatProperty(
        name="Angle Offset",
        description="Starting angle offset in radians",
        default=0.0,
    )

    keep_original: bpy.props.BoolProperty(
        name="Keep Original",
        description="Whether to keep the source object",
        default=True,
    )

    def execute(self, context):
        # Get source object
        source_obj = bpy.data.objects.get(self.source)
        if not source_obj:
            self.report({'ERROR'}, f"Source object '{self.source}' not found")
            return {'CANCELLED'}

        # Center point
        center = Vector((self.center_x, self.center_y, self.center_z))

        # Calculate angle step
        angle_step = 2.0 * 3.14159265359 / self.count

        # Determine rotation axis
        if self.axis == 'X':
            rot_axis = Vector((1, 0, 0))
        elif self.axis == 'Y':
            rot_axis = Vector((0, 1, 0))
        else:
            rot_axis = Vector((0, 0, 1))

        # Calculate initial offset from center
        offset = source_obj.location - center

        # Determine starting angle from offset if angle_offset is 0 and offset has length
        start_angle = self.angle_offset
        if start_angle == 0.0 and offset.length > 0.0001:
            # Project offset onto plane perpendicular to axis
            if self.axis == 'Z':
                start_angle = offset.to_2d().angle_signed(Vector((1, 0)), 0)
            elif self.axis == 'Y':
                start_angle = Vector((offset.x, offset.z)).angle_signed(Vector((1, 0)), 0)
            else:  # X
                start_angle = Vector((offset.y, offset.z)).angle_signed(Vector((1, 0)), 0)

        created_objects = []
        
        for i in range(self.count):
            if i == 0 and self.keep_original:
                # Keep original at its position
                created_objects.append(source_obj)
                continue

            # Calculate angle for this duplicate
            angle = start_angle + i * angle_step

            # Create duplicate
            if i == 0 and not self.keep_original:
                # First duplicate replaces original position
                dup = source_obj
            else:
                dup = source_obj.copy()
                dup.data = source_obj.data.copy()
                context.collection.objects.link(dup)

            # Rotate offset around axis
            rot_mat = Matrix.Rotation(angle, 4, rot_axis)
            new_offset = rot_mat @ offset
            dup.location = center + new_offset

            # Apply rotation to object
            dup.rotation_euler.rotate(rot_mat)

            created_objects.append(dup)

        self.report({'INFO'}, f"Created {len(created_objects)} radial duplicates of '{self.source}'")
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

        # Read command from text block (multiline support)
        text_block_name = props.ai_command_text_block or "BlenderAICommand"
        text_block = bpy.data.texts.get(text_block_name)
        if text_block:
            user_command = text_block.as_string()
        else:
            # Fallback to legacy single-line property
            user_command = self.command or props.ai_command

        if not user_command.strip():
            self.report({'WARNING'}, "Empty command")
            return {'CANCELLED'}

        # Update status: Sending
        props.ai_status = 'SENDING'
        props.ai_error_message = ""

        # Diagnostic logging for command verification
        print(f"[BlenderAI Diagnostic] Command length: {len(user_command)} chars")
        print(f"[BlenderAI Diagnostic] Newline count: {user_command.count(chr(10))}")
        preview = user_command[:200].replace('\n', '\\n')
        print(f"[BlenderAI Diagnostic] Command preview: {preview}{'...' if len(user_command) > 200 else ''}")

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
    BLENDER_AI_AGENT_OT_edit_command,
    OBJECT_OT_duplicate_radial,
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