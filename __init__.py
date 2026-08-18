bl_info = {
    "name": "Blender AI Agent",
    "author": "Your Name",
    "version": (1, 5, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Blender AI Agent",
    "description": "AI-powered Blender agent with NVIDIA Nemotron integration",
    "category": "Object",
}

from . import operators, panels, properties, utils, ai

def register():
    properties.register()
    operators.register()
    panels.register()
    ai.register()

def unregister():
    ai.unregister()
    panels.unregister()
    operators.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()