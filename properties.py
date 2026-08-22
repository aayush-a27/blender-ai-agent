import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty, PointerProperty
from bpy.types import AddonPreferences, PropertyGroup


class BlenderAIAgentPreferences(AddonPreferences):
    bl_idname = __package__

    api_key: StringProperty(
        name="NVIDIA API Key",
        description="API key for NVIDIA Nemotron (stored in Blender preferences, not in source)",
        default="",
        subtype='PASSWORD',
    )

    api_endpoint: StringProperty(
        name="API Endpoint",
        description="NVIDIA API endpoint",
        default="https://integrate.api.nvidia.com/v1",
    )

    model_name: StringProperty(
        name="Model",
        description="Nemotron model to use",
        default="nvidia/nemotron-3-ultra-550b-a55b",
    )

    max_tokens: IntProperty(
        name="Max Tokens",
        description="Maximum tokens for AI response",
        default=1024,
        min=1,
        max=8192,
    )

    temperature: bpy.props.FloatProperty(
        name="Temperature",
        description="Sampling temperature",
        default=0.1,
        min=0.0,
        max=2.0,
        step=0.1,
        precision=2,
    )

    request_timeout: IntProperty(
        name="Request Timeout (s)",
        description="Total request timeout in seconds for API calls. Increase for complex scene generation.",
        default=120,
        min=30,
        max=300,
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="NVIDIA Nemotron API Configuration", icon='PREFERENCES')
        layout.prop(self, "api_key")
        layout.prop(self, "api_endpoint")
        layout.prop(self, "model_name")
        layout.prop(self, "max_tokens")
        layout.prop(self, "temperature")
        layout.prop(self, "request_timeout")
        layout.separator()
        
        # Test Connection button
        row = layout.row()
        row.scale_y = 1.2
        op = row.operator("blender_ai_agent.test_connection", text="Test Connection", icon='URL')
        
        layout.separator()
        layout.label(text="Get API key at: https://build.nvidia.com", icon='URL')


class BlenderAIAgentProperties(PropertyGroup):
    ai_command: StringProperty(
        name="AI Command",
        description="Natural language command for the AI agent (legacy single-line, kept for compatibility)",
        default="",
        maxlen=2000,
    )

    ai_command_text_block: StringProperty(
        name="AI Command Text Block",
        description="Name of the text block used for multiline AI command input",
        default="BlenderAICommand",
        maxlen=64,
    )

    ai_status: EnumProperty(
        name="Status",
        description="Current AI operation status",
        items=[
            ('READY', "Ready", "Ready to accept commands"),
            ('SENDING', "Sending...", "Sending request to API"),
            ('PROCESSING', "Processing...", "Waiting for AI response"),
            ('EXECUTING', "Executing...", "Running Blender operations"),
            ('COMPLETED', "Completed", "Command completed successfully"),
            ('ERROR', "Error", "An error occurred"),
        ],
        default='READY',
    )

    ai_error_message: StringProperty(
        name="Error Message",
        description="Last error message from AI operation",
        default="",
    )


classes = (
    BlenderAIAgentPreferences,
    BlenderAIAgentProperties,
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
    bpy.types.Scene.blender_ai_agent = PointerProperty(type=BlenderAIAgentProperties)


def unregister():
    del bpy.types.Scene.blender_ai_agent
    for cls in reversed(classes):
        _unregister_class_safe(cls)