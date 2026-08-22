# Blender AI Agent - Scene Context Collector
# Collects current Blender scene state for AI context awareness

import bpy
from typing import Dict, Any, List, Optional
from mathutils import Vector


MAX_OBJECTS_IN_CONTEXT = 50
MAX_CONTEXT_CHARS = 8000


def _format_vector(vec: Vector, precision: int = 2) -> List[float]:
    """Format a vector as a list of rounded floats."""
    return [round(v, precision) for v in vec]


def _format_euler(euler) -> List[float]:
    """Format euler rotation as degrees for readability."""
    import math
    return [round(math.degrees(v), 1) for v in euler]


def _get_bounding_box(obj: bpy.types.Object) -> Optional[Dict[str, List[float]]]:
    """Get world-space bounding box of an object."""
    if not obj or not obj.bound_box:
        return None
    
    # Transform bounding box corners to world space
    world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    
    # Calculate min/max for each axis
    xs = [c.x for c in world_corners]
    ys = [c.y for c in world_corners]
    zs = [c.z for c in world_corners]
    
    min_corner = [min(xs), min(ys), min(zs)]
    max_corner = [max(xs), max(ys), max(zs)]
    size = [max_corner[i] - min_corner[i] for i in range(3)]
    center = [(min_corner[i] + max_corner[i]) / 2.0 for i in range(3)]
    
    return {
        "min": _format_vector(min_corner),
        "max": _format_vector(max_corner),
        "size": _format_vector(size),
        "center": _format_vector(center),
    }


def _format_vector(vec: Vector, precision: int = 2) -> List[float]:
    """Format a vector as a list of rounded floats."""
    return [round(v, precision) for v in vec]


def _format_euler(euler) -> List[float]:
    """Format euler rotation as degrees for readability."""
    import math
    return [round(math.degrees(v), 1) for v in euler]


def _get_object_summary(obj: bpy.types.Object) -> Dict[str, Any]:
    """Extract a compact summary of an object."""
    summary = {
        "name": obj.name,
        "type": obj.type,
        "location": _format_vector(obj.location),
        "rotation": _format_euler(obj.rotation_euler),
        "scale": _format_vector(obj.scale),
    }
    
    # Add bounding box for spatial reasoning
    bbox = _get_bounding_box(obj)
    if bbox:
        summary["bounding_box"] = bbox
    
    # Add type-specific info
    if obj.type == 'MESH':
        summary["mesh"] = {
            "vertices": len(obj.data.vertices) if obj.data else 0,
            "faces": len(obj.data.polygons) if obj.data else 0,
        }
    elif obj.type == 'LIGHT':
        light_data = obj.data
        summary["light"] = {
            "type": light_data.type,
            "energy": round(light_data.energy, 2),
            "color": _format_vector(Vector(light_data.color), 2),
        }
    elif obj.type == 'CAMERA':
        cam_data = obj.data
        summary["camera"] = {
            "lens": round(cam_data.lens, 1),
            "sensor_width": round(cam_data.sensor_width, 1),
        }
    
    return summary


def _get_active_object_name() -> Optional[str]:
    """Get name of active object."""
    active = bpy.context.active_object
    return active.name if active else None


def _get_selected_object_names() -> List[str]:
    """Get names of selected objects."""
    return [obj.name for obj in bpy.context.selected_objects]


def _get_cameras() -> List[Dict[str, Any]]:
    """Get all cameras in scene."""
    return [_get_object_summary(obj) for obj in bpy.context.scene.objects if obj.type == 'CAMERA']


def _get_lights() -> List[Dict[str, Any]]:
    """Get all lights in scene."""
    return [_get_object_summary(obj) for obj in bpy.context.scene.objects if obj.type == 'LIGHT']


def _get_meshes() -> List[Dict[str, Any]]:
    """Get all mesh objects in scene."""
    return [_get_object_summary(obj) for obj in bpy.context.scene.objects if obj.type == 'MESH']


def collect_scene_context() -> Dict[str, Any]:
    """
    Collect current Blender scene state for AI context.
    
    Returns a compact structured representation of the scene including logical groups.
    """
    scene = bpy.context.scene
    objects = scene.objects
    
    # Count objects by type
    type_counts = {}
    for obj in objects:
        type_counts[obj.type] = type_counts.get(obj.type, 0) + 1
    
    # Get active and selected
    active_name = _get_active_object_name()
    selected_names = _get_selected_object_names()
    
    # Detect logical groups by name prefix
    groups = _detect_logical_groups(objects)
    
    # Get key object lists (limited)
    cameras = _get_cameras()
    lights = _get_lights()
    meshes = _get_meshes()
    
    # Build context
    context = {
        "scene_name": scene.name,
        "object_count": len(objects),
        "type_counts": type_counts,
        "active_object": active_name,
        "selected_objects": selected_names,
        "cameras": cameras[:5],  # Limit to 5
        "lights": lights[:5],    # Limit to 5
        "meshes": meshes[:MAX_OBJECTS_IN_CONTEXT],  # Limit meshes
        "groups": groups[:10],   # Limit groups
    }
    
    # Truncate if too large
    import json
    context_json = json.dumps(context)
    if len(context_json) > MAX_CONTEXT_CHARS:
        # Reduce mesh details
        for mesh in context["meshes"]:
            if "mesh" in mesh:
                del mesh["mesh"]
        context_json = json.dumps(context)
        
        # If still too large, truncate meshes list
        if len(context_json) > MAX_CONTEXT_CHARS:
            context["meshes"] = context["meshes"][:20]
            context_json = json.dumps(context)
            
            # Last resort: remove mesh list entirely
            if len(context_json) > MAX_CONTEXT_CHARS:
                context["meshes"] = []
                context_json = json.dumps(context)
    
    return context


def _detect_logical_groups(objects) -> List[Dict[str, Any]]:
    """Detect logical groups by analyzing Blender parent hierarchy.
    
    A group is an object that has children (is a parent). The root object
    is the parent, and its children (and their descendants) are the components.
    """
    groups = {}
    
    for obj in objects:
        # Check if this object is a root (has children)
        if obj.children:
            group_name = obj.name
            
            if group_name not in groups:
                groups[group_name] = {
                    "name": group_name,
                    "components": [],
                    "object_count": 0,
                    "types": set(),
                    "root_type": obj.type,
                }
            
            group = groups[group_name]
            
            # Collect all descendants (children, grandchildren, etc.)
            def collect_descendants(obj, group_data):
                for child in obj.children:
                    group_data["components"].append(child.name)
                    group_data["object_count"] += 1
                    group_data["types"].add(child.type)
                    collect_descendants(child, group_data)
            
            collect_descendants(obj, groups[group_name])
    
    # Convert to list format
    group_list = []
    for group_name, group_data in groups.items():
        if group_data["object_count"] > 1:  # Only include groups with multiple objects
            group_list.append({
                "name": group_name,
                "component_count": group_data["object_count"],
                "components": group_data["components"][:10],  # Limit components
                "types": list(group_data["types"]),
                "root_type": group_data.get("root_type", "UNKNOWN"),
            })
    
    # Sort by component count (largest groups first)
    group_list.sort(key=lambda g: g["component_count"], reverse=True)
    
    return group_list


def format_scene_context_for_prompt(context: Dict[str, Any]) -> str:
    """
    Format scene context as a compact data reference for prompt injection.
    Uses structured format to discourage natural language responses.
    Includes bounding box for spatial reasoning and logical groups.
    """
    lines = []
    
    lines.append("SCENE_CONTEXT_BEGIN")
    lines.append(f"scene_name: {context['scene_name']}")
    lines.append(f"object_count: {context['object_count']}")
    
    if context["type_counts"]:
        type_str = ", ".join(f"{k}:{v}" for k, v in sorted(context["type_counts"].items()))
        lines.append(f"type_counts: {type_str}")
    
    if context["active_object"]:
        lines.append(f"active_object: {context['active_object']}")
    
    if context["selected_objects"]:
        sel = ", ".join(context["selected_objects"][:10])
        lines.append(f"selected_objects: {sel}")
    
    # Logical groups
    if context.get("groups"):
        lines.append(f"group_count: {len(context['groups'])}")
        for group in context["groups"][:10]:
            comps = ", ".join(group["components"][:8])
            lines.append(f"group: name={group['name']}, components={group['component_count']}, items=[{comps}]")
        if len(context["groups"]) > 10:
            lines.append(f"group_remaining: {len(context['groups']) - 10}")
    
    if context["cameras"]:
        for cam in context["cameras"]:
            loc = cam["location"]
            lens = cam.get("camera", {}).get("lens", 0)
            lines.append(f"camera: name={cam['name']}, location={loc}, lens={lens}")
    
    if context["lights"]:
        for light in context["lights"]:
            loc = light["location"]
            ltype = light.get("light", {}).get("type", "POINT")
            energy = light.get("light", {}).get("energy", 0)
            color = light.get("light", {}).get("color", [1,1,1])
            lines.append(f"light: name={light['name']}, type={ltype}, energy={energy}, color={color}, location={loc}")
    
    if context["meshes"]:
        lines.append(f"mesh_count: {len(context['meshes'])}")
        for mesh in context["meshes"][:15]:
            loc = mesh["location"]
            rot = mesh["rotation"]
            sc = mesh["scale"]
            bbox = mesh.get("bounding_box")
            bbox_str = ""
            if bbox:
                bbox_str = f", bbox_size={bbox['size']}, bbox_center={bbox['center']}"
            lines.append(f"mesh: name={mesh['name']}, location={loc}, rotation={rot}, scale={sc}{bbox_str}")
        if len(context["meshes"]) > 15:
            lines.append(f"mesh_remaining: {len(context['meshes']) - 15}")
    
    lines.append("SCENE_CONTEXT_END")
    
    return "\n".join(lines)