bl_info = {
    "name": "Blender AI Agent",
    "author": "Your Name",
    "version": (1, 5, 2),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Blender AI Agent",
    "description": "AI-powered Blender agent with NVIDIA Nemotron integration",
    "category": "Object",
}

from . import operators, panels, properties, utils, ai
import sys

def _purge_blender_ai_agent_modules():
    """Remove all blender_ai_agent modules from sys.modules to force reload."""
    to_remove = [name for name in sys.modules if name.startswith('blender_ai_agent')]
    for name in to_remove:
        del sys.modules[name]
    print(f"[BlenderAI Diagnostic] Purged {len(to_remove)} modules from sys.modules: {to_remove}")


def _diagnose_runtime():
    """Run runtime diagnostics to identify which files are actually loaded."""
    import sys
    import os
    import inspect
    
    print("=" * 60)
    print("[BlenderAI Diagnostic] RUNTIME DIAGNOSTIC START")
    print("=" * 60)
    
    # Check sys.modules
    print("\n[BlenderAI Diagnostic] === SYS.MODULES ===")
    for name in sorted(sys.modules.keys()):
        if 'blender_ai' in name.lower():
            mod = sys.modules[name]
            filepath = getattr(mod, '__file__', 'NO __file__')
            print(f"  {name}: {filepath}")

    # Check addon path
    addon_path = r'C:\Users\PC\AppData\Roaming\Blender Foundation\Blender\4.0\scripts\addons\blender-ai-agent'
    print(f"\n[BlenderAI Diagnostic] Addon path exists: {os.path.exists(addon_path)}")
    print(f"[BlenderAI Diagnostic] Addon path: {addon_path}")
    
    actions_path = os.path.join(addon_path, 'ai', 'actions.py')
    print(f"[BlenderAI Diagnostic] actions.py exists on disk: {os.path.exists(actions_path)}")
    
    if os.path.exists(actions_path):
        with open(actions_path, 'r') as f:
            content = f.read()
        has_fix = 'requested_name = action.get("name")' in content and 'obj.name = requested_name' in content
        print(f"[BlenderAI Diagnostic] On disk - _execute_create_object HAS NAME FIX: {has_fix}")

    # Check runtime module
    if 'blender_ai_agent.ai.actions' in sys.modules:
        mod = sys.modules['blender_ai_agent.ai.actions']
        print(f"\n[BlenderAI Diagnostic] Runtime module file: {getattr(mod, '__file__', 'NO __FILE__')}")
        
        if hasattr(mod, '_execute_create_object'):
            import inspect
            source = inspect.getsource(mod._execute_create_object)
            has_fix = 'requested_name = action.get("name")' in source and 'obj.name = requested_name' in source
            print(f"[BlenderAI Diagnostic] Runtime _execute_create_object HAS NAME FIX: {has_fix}")
            if not has_fix:
                print("[BlenderAI Diagnostic] *** RUNTIME FUNCTION MISSING THE FIX! ***")
                # Show relevant portion
                import inspect
                source = inspect.getsource(mod._execute_create_object)
                idx = source.find('obj = bpy.context.active_object')
                if idx >= 0:
                    print("[BlenderAI Diagnostic] Runtime function content around obj assignment:")
                    print(source[idx:idx+300])
    else:
        print("\n[BlenderAI Diagnostic] ERROR: blender_ai_agent.ai.actions NOT in sys.modules!")

    # Check for duplicates
    print("\n[BlenderAI Diagnostic] === DUPLICATE MODULE CHECK ===")
    for name in sorted(sys.modules.keys()):
        if 'blender_ai' in name.lower():
            mod = sys.modules[name]
            filepath = getattr(mod, '__file__', 'NO __FILE__')
            print(f"  {name}: {filepath}")

    print("\n[BlenderAI Diagnostic] === DIAGNOSTIC COMPLETE ===")


def register():
    print("[BlenderAI] Registering addon v1.5.2...")
    
    # Run diagnostics first
    _diagnose_runtime()
    
    # Purge old modules first to ensure fresh imports
    _purge_blender_ai_agent_modules()
    
    print("[BlenderAI] Registering addon...")
    from . import properties, operators, panels, ai
    properties.register()
    operators.register()
    panels.register()
    ai.register()
    
    # Post-registration verification
    if 'blender_ai_agent.ai.actions' in sys.modules:
        mod = sys.modules['blender_ai_agent.ai.actions']
        if hasattr(mod, '_execute_create_object'):
            import inspect
            source = inspect.getsource(mod._execute_create_object)
            has_fix = 'requested_name = action.get("name")' in source and 'obj.name = requested_name' in source
            print(f"[BlenderAI Diagnostic] Post-registration _execute_create_object HAS NAME FIX: {has_fix}")
            if not has_fix:
                print("!!! POST-REGISTRATION: _execute_create_object STILL MISSING THE FIX !!!")
                import inspect
                source = inspect.getsource(mod._execute_create_object)
                idx = source.find('obj = bpy.context.active_object')
                if idx >= 0:
                    print(source[idx:idx+300])

    print("[BlenderAI] Addon registration complete.")


def unregister():
    print("[BlenderAI] Unregistering addon...")
    from . import ai, panels, operators, properties
    ai.unregister()
    panels.unregister()
    operators.unregister()
    properties.unregister()
    _purge_blender_ai_agent_modules()
    print("[BlenderAI] Addon unregistered.")


if __name__ == "__main__":
    register()