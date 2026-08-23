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


class OBJECT_OT_duplicate_linear(Operator):
    """Duplicate an object linearly along an axis."""
    bl_idname = "object.duplicate_linear"
    bl_label = "Duplicate Linear"
    bl_description = "Create linear duplicates of an object along an axis"
    bl_options = {'REGISTER', 'UNDO'}

    source: bpy.props.StringProperty(
        name="Source Object",
        description="Name of the source object to duplicate",
        default="",
    )

    count: bpy.props.IntProperty(
        name="Count",
        description="Number of total objects (including original if keep_original)",
        default=5,
        min=2,
        max=100,
    )

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis for linear distribution",
        items=[
            ('X', "X", "Distribute along X axis"),
            ('Y', "Y", "Distribute along Y axis"),
            ('Z', "Z", "Distribute along Z axis"),
        ],
        default='Z',
    )

    spacing: bpy.props.FloatProperty(
        name="Spacing",
        description="Distance between duplicates along the axis",
        default=1.0,
        min=0.001,
        max=1000.0,
    )

    start_offset_x: bpy.props.FloatProperty(
        name="Start Offset X",
        description="X offset for the first duplicate relative to source",
        default=0.0,
    )

    start_offset_y: bpy.props.FloatProperty(
        name="Start Offset Y",
        description="Y offset for the first duplicate relative to source",
        default=0.0,
    )

    start_offset_z: bpy.props.FloatProperty(
        name="Start Offset Z",
        description="Z offset for the first duplicate relative to source",
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

        # Determine axis vector
        if self.axis == 'X':
            axis_vec = Vector((1, 0, 0))
        elif self.axis == 'Y':
            axis_vec = Vector((0, 1, 0))
        else:
            axis_vec = Vector((0, 0, 1))

        # Calculate start offset vector
        start_offset = Vector((self.start_offset_x, self.start_offset_y, self.start_offset_z))

        created_objects = []
        
        for i in range(self.count):
            if i == 0 and self.keep_original:
                # Keep original at its position
                created_objects.append(source_obj)
                continue

            # Calculate position for this duplicate
            # If keep_original=True and i=0, we skip. So first duplicate is at i=1 (if keep_original) or i=0 (if not)
            duplicate_index = i if not self.keep_original else i - 1
            
            # Position = source_location + start_offset + (duplicate_index + 1) * spacing * axis_vec
            # Actually, if we want the first duplicate to be at source + start_offset + spacing*axis:
            if self.keep_original:
                offset_distance = (duplicate_index + 1) * self.spacing
            else:
                offset_distance = (duplicate_index + 1) * self.spacing
            
            position = source_obj.location + start_offset + axis_vec * offset_distance

            # Create duplicate
            if i == 0 and not self.keep_original:
                # First duplicate replaces original position
                dup = source_obj
            else:
                dup = source_obj.copy()
                dup.data = source_obj.data.copy()
                context.collection.objects.link(dup)

            dup.location = position
            # Keep same rotation and scale as source
            dup.rotation_euler = source_obj.rotation_euler.copy()
            dup.scale = source_obj.scale.copy()

            created_objects.append(dup)

        self.report({'INFO'}, f"Created {len(created_objects)} linear duplicates of '{self.source}' along {self.axis}")
        return {'FINISHED'}


class OBJECT_OT_mirror_object(Operator):
    """Create a mirrored copy of an object across a plane."""
    bl_idname = "object.mirror_object"
    bl_label = "Mirror Object"
    bl_description = "Create a mirrored copy of an object across a plane"
    bl_options = {'REGISTER', 'UNDO'}

    source: bpy.props.StringProperty(
        name="Source Object",
        description="Name of the source object to mirror",
        default="",
    )

    plane: bpy.props.EnumProperty(
        name="Plane",
        description="Mirror plane (XY, YZ, or XZ)",
        items=[
            ('XY', "XY", "Mirror across XY plane (Z axis normal)"),
            ('YZ', "YZ", "Mirror across YZ plane (X axis normal)"),
            ('XZ', "XZ", "Mirror across XZ plane (Y axis normal)"),
        ],
        default='YZ',
    )

    offset: bpy.props.FloatProperty(
        name="Offset",
        description="Plane offset from origin along the normal axis",
        default=0.0,
    )

    merge: bpy.props.BoolProperty(
        name="Merge",
        description="Whether to merge the mirrored object with the source (for closed meshes)",
        default=False,
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

        # Determine mirror plane normal and axis
        if self.plane == 'XY':
            # Mirror across XY plane -> flip Z
            normal_axis = Vector((0, 0, 1))
            mirror_axis = 'Z'
        elif self.plane == 'YZ':
            # Mirror across YZ plane -> flip X
            normal_axis = Vector((1, 0, 0))
            mirror_axis = 'X'
        else:  # XZ
            # Mirror across XZ plane -> flip Y
            normal_axis = Vector((0, 1, 0))
            mirror_axis = 'Y'

        # Create mirrored object
        if not self.keep_original:
            # Use source object itself as the mirrored object
            mirror_obj = source_obj
        else:
            mirror_obj = source_obj.copy()
            mirror_obj.data = source_obj.data.copy()
            context.collection.objects.link(mirror_obj)

        # Calculate mirrored position
        # Mirror the location across the plane
        source_loc = source_obj.location
        plane_normal = normal_axis
        plane_offset = self.offset

        # Distance from source to plane along normal
        dist = (source_loc - plane_normal * plane_offset).dot(plane_normal)
        # Mirrored position: source - 2 * dist * normal
        mirrored_loc = source_loc - 2 * dist * plane_normal

        # Apply mirrored location
        mirror_obj.location = mirrored_loc

        # Mirror the rotation/scale along the normal axis
        # For rotation: flip the rotation component along the mirror axis
        # For scale: flip the scale component along the mirror axis (negative scale)
        if mirror_axis == 'X':
            mirror_obj.scale.x = -mirror_obj.scale.x
            mirror_obj.rotation_euler.x = -mirror_obj.rotation_euler.x
        elif mirror_axis == 'Y':
            mirror_obj.scale.y = -mirror_obj.scale.y
            mirror_obj.rotation_euler.y = -mirror_obj.rotation_euler.y
        else:  # Z
            mirror_obj.scale.z = -mirror_obj.scale.z
            mirror_obj.rotation_euler.z = -mirror_obj.rotation_euler.z

        # Generate unique name for mirrored object
        if self.keep_original:
            base_name = self.source
            # Find a unique name
            counter = 1
            while f"{base_name}_Mirrored_{counter:03d}" in bpy.data.objects:
                counter += 1
            mirror_obj.name = f"{base_name}_Mirrored_{counter:03d}"
        else:
            mirror_obj.name = self.source

        # Handle merge option (if merge is True and keep_original is True, join the objects)
        if self.merge and self.keep_original:
            # Deselect all
            bpy.ops.object.select_all(action='DESELECT')
            # Select both objects
            source_obj.select_set(True)
            mirror_obj.select_set(True)
            # Set source as active
            context.view_layer.objects.active = source_obj
            # Join them
            bpy.ops.object.join()
            self.report({'INFO'}, f"Mirrored and merged '{self.source}' across {self.plane} plane")
        else:
            self.report({'INFO'}, f"Mirrored '{self.source}' across {self.plane} plane")

        return {'FINISHED'}


class OBJECT_OT_align_objects(Operator):
    """Align source object relative to target object using world-space bounding boxes."""
    bl_idname = "object.align_objects"
    bl_label = "Align Objects"
    bl_description = "Align source object relative to target object using world-space bounding boxes"
    bl_options = {'REGISTER', 'UNDO'}

    source: bpy.props.StringProperty(
        name="Source Object",
        description="Name of the source object to align",
        default="",
    )

    target: bpy.props.StringProperty(
        name="Target Object",
        description="Name of the target object to align to",
        default="",
    )

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis along which to align",
        items=[
            ('X', "X", "Align along X axis"),
            ('Y', "Y", "Align along Y axis"),
            ('Z', "Z", "Align along Z axis"),
        ],
        default='Z',
    )

    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Alignment mode: MIN (min bounds), CENTER (centers), MAX (max bounds)",
        items=[
            ('MIN', "MIN", "Align minimum bounds"),
            ('CENTER', "CENTER", "Align centers"),
            ('MAX', "MAX", "Align maximum bounds"),
        ],
        default='CENTER',
    )

    def execute(self, context):
        # Get source and target objects
        source_obj = bpy.data.objects.get(self.source)
        if not source_obj:
            self.report({'ERROR'}, f"Source object '{self.source}' not found")
            return {'CANCELLED'}

        target_obj = bpy.data.objects.get(self.target)
        if not target_obj:
            self.report({'ERROR'}, f"Target object '{self.target}' not found")
            return {'CANCELLED'}

        # Calculate world-space bounding boxes
        source_bbox = [source_obj.matrix_world @ Vector(corner) for corner in source_obj.bound_box]
        target_bbox = [target_obj.matrix_world @ Vector(corner) for corner in target_obj.bound_box]

        # Extract min/max/center for the specified axis
        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[self.axis]

        source_coords = [c[axis_idx] for c in source_bbox]
        target_coords = [c[axis_idx] for c in target_bbox]

        source_min = min(source_coords)
        source_max = max(source_coords)
        source_center = (source_min + source_max) / 2

        target_min = min(target_coords)
        target_max = max(target_coords)
        target_center = (target_min + target_max) / 2

        # Calculate the desired world-space coordinate for the source's center on the alignment axis
        if self.mode == 'MIN':
            desired_world_coord = target_min
        elif self.mode == 'MAX':
            desired_world_coord = target_max
        else:  # CENTER
            desired_world_coord = target_center

        # Current world-space coordinate of source's center on this axis
        current_world_coord = source_center if self.mode == 'CENTER' else (source_min if self.mode == 'MIN' else source_max)

        # World-space offset needed on this axis
        world_offset = desired_world_coord - current_world_coord

        # Compute the object's current world-space AABB center (full 3D vector)
        # For the alignment axis, use the mode-appropriate value; for other axes, use midpoint
        source_aabb_center_world = Vector((
            source_min if self.axis == 'X' and self.mode == 'MIN' else 
            source_max if self.axis == 'X' and self.mode == 'MAX' else 
            source_center if self.axis == 'X' else (source_coords[0] + source_coords[-1]) / 2,
            source_min if self.axis == 'Y' and self.mode == 'MIN' else 
            source_max if self.axis == 'Y' and self.mode == 'MAX' else 
            source_center if self.axis == 'Y' else (source_coords[0] + source_coords[-1]) / 2,
            source_min if self.axis == 'Z' and self.mode == 'MIN' else 
            source_max if self.axis == 'Z' and self.mode == 'MAX' else 
            source_center if self.axis == 'Z' else (source_coords[0] + source_coords[-1]) / 2
        ))
        
        # Actually, let's simplify: compute full 3D source AABB center in world space
        source_aabb_center_world = sum((Vector(c) for c in source_bbox), Vector()) / 8
        
        source_origin_world = source_obj.matrix_world.translation
        aabb_center_offset = source_aabb_center_world - source_origin_world

        # Desired world-space position of object's origin
        # The target coordinate on the alignment axis is desired_world_coord
        # The current AABB center on that axis is current_world_coord
        # The offset to apply is world_offset = desired - current
        # The origin should move by the same offset (since AABB moves with origin)
        axis_vec = Vector((1, 0, 0)) if self.axis == 'X' else Vector((0, 1, 0)) if self.axis == 'Y' else Vector((0, 0, 1))
        world_offset = desired_world_coord - current_world_coord
        world_offset_vec = axis_vec * world_offset
        
        desired_origin_world = source_origin_world + world_offset_vec

        # Convert desired world origin to local space
        if source_obj.parent:
            parent_mat_inv = source_obj.parent.matrix_world.inverted()
            desired_local_loc = parent_mat_inv @ desired_origin_world
            source_obj.location = desired_local_loc
        else:
            source_obj.location = desired_origin_world

        self.report({'INFO'}, f"Aligned '{self.source}' to '{self.target}' on {self.axis} axis ({self.mode} mode)")
        return {'FINISHED'}


class OBJECT_OT_place_on(Operator):
    """Place source object against target object using world-space bounding boxes."""
    bl_idname = "object.place_on"
    bl_label = "Place On"
    bl_description = "Place source object against target object using world-space bounding boxes"
    bl_options = {'REGISTER', 'UNDO'}

    source: bpy.props.StringProperty(
        name="Source Object",
        description="Name of the source object to place",
        default="",
    )

    target: bpy.props.StringProperty(
        name="Target Object",
        description="Name of the target object to place against",
        default="",
    )

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis along which to place (Z=on top, X=against X, Y=against Y)",
        items=[
            ('X', "X", "Place against X axis"),
            ('Y', "Y", "Place against Y axis"),
            ('Z', "Z", "Place on top (Z axis)"),
        ],
        default='Z',
    )

    offset: bpy.props.FloatProperty(
        name="Offset",
        description="Additional offset from contact point",
        default=0.0,
    )

    def execute(self, context):
        # Get source and target objects
        source_obj = bpy.data.objects.get(self.source)
        if not source_obj:
            self.report({'ERROR'}, f"Source object '{self.source}' not found")
            return {'CANCELLED'}

        target_obj = bpy.data.objects.get(self.target)
        if not target_obj:
            self.report({'ERROR'}, f"Target object '{self.target}' not found")
            return {'CANCELLED'}

        # Calculate world-space bounding boxes
        source_bbox = [source_obj.matrix_world @ Vector(corner) for corner in source_obj.bound_box]
        target_bbox = [target_obj.matrix_world @ Vector(corner) for corner in target_obj.bound_box]

        axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[self.axis]

        source_coords = [c[axis_idx] for c in source_bbox]
        target_coords = [c[axis_idx] for c in target_bbox]

        source_min = min(source_coords)
        source_max = max(source_coords)
        target_min = min(target_coords)
        target_max = max(target_coords)

        # Calculate placement: source's min/max should touch target's max/min + offset
        # For Z: source bottom = target top + offset
        # For X: source min X = target max X + offset
        # For Y: source min Y = target max Y + offset
        
        if self.axis == 'Z':
            # Place on top: source bottom = target top + offset
            world_offset = target_max - source_min + self.offset
            axis_vec = Vector((0, 0, 1))
        elif self.axis == 'X':
            # Place against X: source min X = target max X + offset
            world_offset = target_max - source_min + self.offset
            axis_vec = Vector((1, 0, 0))
        else:  # Y
            # Place against Y: source min Y = target max Y + offset
            world_offset = target_max - source_min + self.offset
            axis_vec = Vector((0, 1, 0))

        world_offset_vec = axis_vec * world_offset

        # Convert world-space offset to object's local space
        if source_obj.parent:
            # Object has parent: location is relative to parent
            # Convert world offset to parent-relative space using 3x3 rotation+scale part
            # parent.matrix_world.inverted() includes translation which is wrong for direction vectors
            # Use 3x3 rotation+scale part: parent.matrix_world.to_3x3().inverted()
            parent_3x3_inv = source_obj.parent.matrix_world.to_3x3().inverted()
            local_offset_vec = parent_3x3_inv @ world_offset_vec
            source_obj.location = source_obj.location + local_offset_vec
        else:
            source_obj.location = source_obj.location + world_offset_vec

        self.report({'INFO'}, f"Placed '{self.source}' on '{self.target}' along {self.axis} axis with offset {self.offset}")
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
    OBJECT_OT_duplicate_linear,
    OBJECT_OT_mirror_object,
    OBJECT_OT_align_objects,
    OBJECT_OT_place_on,
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