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

        row = box.row()
        row.prop(props, "ai_command", text="")

        row = box.row()
        row.scale_y = 1.5
        op = row.operator("object.ai_command", text="Execute", icon='PLAY')
        op.command = props.ai_command

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