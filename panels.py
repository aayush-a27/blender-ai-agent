import bpy
from bpy.types import Panel


class VIEW3D_PT_blender_ai_agent(Panel):
    bl_idname = "VIEW3D_PT_blender_ai_agent"
    bl_label = "Blender AI Agent"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Blender AI Agent'

    def draw(self, context):
        layout = self.layout
        props = context.scene.blender_ai_agent

        # AI Command Section
        box = layout.box()
        box.label(text="AI Command", icon='CONSOLE')

        # Use default text block name (property default is "BlenderAICommand")
        text_block_name = props.ai_command_text_block or "BlenderAICommand"
        text_block = bpy.data.texts.get(text_block_name)
        if text_block is None:
            # Text block will be created lazily by operators when needed
            text_block = bpy.data.texts.new(name=text_block_name)

        # Command preview (first few lines) + Edit button
        cmd_text = text_block.as_string()
        lines = cmd_text.split('\n')
        preview_lines = lines[:5]
        preview = '\n'.join(preview_lines)
        if len(lines) > 5:
            preview += f"\n... ({len(lines)} lines total)"

        # Show preview in a label (read-only, multiline via line breaks)
        if preview.strip():
            for line in preview.split('\n'):
                row = box.row()
                row.enabled = False
                row.label(text=line)
        else:
            row = box.row()
            row.enabled = False
            row.label(text="(empty - click Edit Command to write)")

        # Edit Command button opens Text Editor
        row = box.row()
        row.operator("blender_ai_agent.edit_command", text="Edit Command", icon='TEXT')

        # Execute button
        row = box.row()
        row.scale_y = 1.5
        op = row.operator("object.ai_command", text="Execute", icon='PLAY')
        op.command = ""

        # Status display
        status_row = box.row()
        status_row.enabled = False
        status_icon = self._get_status_icon(props.ai_status)
        status_row.label(text=f"Status: {props.ai_status.replace('_', ' ').title()}", icon=status_icon)

        if props.ai_status == 'ERROR' and props.ai_error_message:
            err_box = box.box()
            err_box.alert = True
            err_box.label(text=props.ai_error_message, icon='ERROR')

        layout.separator()

        # Object Creation Section
        box = layout.box()
        box.label(text="Create Objects", icon='MESH_CUBE')

        row = box.row(align=True)
        row.operator("object.create_cube", icon='MESH_CUBE')
        row.operator("object.create_sphere", icon='MESH_UVSPHERE')
        row.operator("object.create_cylinder", icon='MESH_CYLINDER')

        # Object Manipulation Section
        box = layout.box()
        box.label(text="Modify Scene", icon='X')

        row = box.row(align=True)
        row.operator("object.delete_selected", icon='TRASH')
        row.operator("object.clear_scene", icon='SCENE_DATA')

    def _get_status_icon(self, status):
        icons = {
            'READY': 'CHECKMARK',
            'SENDING': 'TIME',
            'PROCESSING': 'TIME',
            'EXECUTING': 'TIME',
            'COMPLETED': 'CHECKMARK',
            'ERROR': 'ERROR',
        }
        return icons.get(status, 'INFO')


classes = (VIEW3D_PT_blender_ai_agent,)


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