# Blender AI Agent - Procedural Material Creation
import bpy
from mathutils import Vector


# Stable material names for reuse
WOOD_MATERIAL_NAMES = {
    "wood": "AI_Wood",
    "light_wood": "AI_Light_Wood",
    "dark_wood": "AI_Dark_Wood",
}

# Supported material presets
SUPPORTED_WOOD_PRESETS = set(WOOD_MATERIAL_NAMES.keys())


def get_or_create_wood_material(preset: str):
    """
    Get existing wood material or create a new procedural wood material.
    
    Args:
        preset: One of "wood", "light_wood", "dark_wood"
        
    Returns:
        bpy.types.Material: The wood material
    """
    if preset not in WOOD_MATERIAL_NAMES:
        raise ValueError(f"Unsupported wood preset: {preset}. Supported: {list(SUPPORTED_WOOD_PRESETS)}")
    
    material_name = WOOD_MATERIAL_NAMES[preset]
    mat = bpy.data.materials.get(material_name)
    
    if mat:
        return mat
    
    # Create new procedural wood material
    mat = bpy.data.materials.new(name=material_name)
    mat.use_nodes = True
    
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Create nodes
    tex_coord = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    noise_1 = nodes.new('ShaderNodeTexNoise')
    noise_2 = nodes.new('ShaderNodeTexNoise')
    wave_tex = nodes.new('ShaderNodeTexWave')
    color_ramp_1 = nodes.new('ShaderNodeValToRGB')
    color_ramp_2 = nodes.new('ShaderNodeValToRGB')
    bump = nodes.new('ShaderNodeBump')
    mix_rgb = nodes.new('ShaderNodeMixRGB')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    output = nodes.new('ShaderNodeOutputMaterial')
    
    # Position nodes for readability
    tex_coord.location = (-1200, 200)
    mapping.location = (-1000, 200)
    noise_1.location = (-800, 300)
    noise_2.location = (-800, -100)
    wave_tex.location = (-800, 100)
    color_ramp_1.location = (-550, 300)
    color_ramp_2.location = (-550, -100)
    bump.location = (-300, 100)
    mix_rgb.location = (-50, 200)
    bsdf.location = (200, 200)
    output.location = (400, 200)
    
    # Configure mapping for grain direction
    mapping.inputs['Scale'].default_value = (4.0, 0.8, 4.0)
    mapping.inputs['Rotation'].default_value = (0.0, 0.0, 0.0)
    
    # Primary wood grain noise (elongated)
    noise_1.noise_dimensions = '3D'
    noise_1.inputs['Scale'].default_value = 15.0
    noise_1.inputs['Detail'].default_value = 6.0
    noise_1.inputs['Roughness'].default_value = 0.6
    noise_1.inputs['Distortion'].default_value = 0.3
    
    # Secondary noise for color variation
    noise_2.noise_dimensions = '3D'
    noise_2.inputs['Scale'].default_value = 5.0
    noise_2.inputs['Detail'].default_value = 3.0
    noise_2.inputs['Roughness'].default_value = 0.5
    noise_2.inputs['Distortion'].default_value = 0.2
    
    # Wave texture for grain lines
    wave_tex.wave_type = 'BANDS'
    wave_tex.wave_profile = 'SAW'
    wave_tex.inputs['Scale'].default_value = 30.0
    wave_tex.inputs['Distortion'].default_value = 2.0
    wave_tex.inputs['Detail'].default_value = 4.0
    wave_tex.inputs['Detail Scale'].default_value = 1.5
    wave_tex.inputs['Detail Roughness'].default_value = 0.75
    
    # ColorRamp 1: Base wood color variation
    color_ramp_1.color_ramp.elements[0].position = 0.0
    color_ramp_1.color_ramp.elements[1].position = 1.0
    
    # ColorRamp 2: Grain lines
    color_ramp_2.color_ramp.elements[0].position = 0.45
    color_ramp_2.color_ramp.elements[1].position = 0.55
    color_ramp_2.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    color_ramp_2.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    
    # Bump for surface detail
    bump.inputs['Strength'].default_value = 0.15
    bump.inputs['Distance'].default_value = 1.0
    
    # Mix RGB for combining grain with base color
    mix_rgb.blend_type = 'OVERLAY'
    mix_rgb.inputs['Fac'].default_value = 0.6
    
    # Configure BSDF based on preset
    _configure_wood_bsdf(bsdf, preset)
    
    # Connect nodes
    # Texture coordinate -> Mapping
    links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
    
    # Mapping -> Noise textures
    links.new(mapping.outputs['Vector'], noise_1.inputs['Vector'])
    links.new(mapping.outputs['Vector'], noise_2.inputs['Vector'])
    links.new(mapping.outputs['Vector'], wave_tex.inputs['Vector'])
    
    # Noise 1 -> ColorRamp 1 (base color variation)
    links.new(noise_1.outputs['Fac'], color_ramp_1.inputs['Fac'])
    
    # Wave -> ColorRamp 2 (grain lines)
    links.new(wave_tex.outputs['Fac'], color_ramp_2.inputs['Fac'])
    
    # ColorRamp 2 -> Bump (grain normal)
    links.new(color_ramp_2.outputs['Color'], bump.inputs['Height'])
    
    # ColorRamp 1 -> Mix RGB (base color)
    links.new(color_ramp_1.outputs['Color'], mix_rgb.inputs['Color1'])
    
    # ColorRamp 2 -> Mix RGB (grain overlay)
    links.new(color_ramp_2.outputs['Color'], mix_rgb.inputs['Color2'])
    
    # Mix RGB -> BSDF Base Color
    links.new(mix_rgb.outputs['Color'], bsdf.inputs['Base Color'])
    
    # Bump -> BSDF Normal
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    
    # Noise 2 -> BSDF Roughness (subtle roughness variation)
    links.new(noise_2.outputs['Fac'], bsdf.inputs['Roughness'])
    
    # BSDF -> Output
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Set preset-specific colors
    _apply_wood_colors(color_ramp_1, preset)
    
    return mat


def _apply_wood_colors(color_ramp: bpy.types.ShaderNodeValToRGB, preset: str):
    """Apply preset-specific color stops to the wood color ramp."""
    # Clear and set up color stops for each preset
    if preset == "light_wood":
        # Light oak/beech - pale warm tones
        color_ramp.color_ramp.elements[0].color = (0.75, 0.62, 0.42, 1.0)
        color_ramp.color_ramp.elements[1].color = (0.88, 0.78, 0.58, 1.0)
        # Add intermediate stops for more variation
        elem = color_ramp.color_ramp.elements.new(0.3)
        elem.color = (0.80, 0.68, 0.48, 1.0)
        elem = color_ramp.color_ramp.elements.new(0.7)
        elem.color = (0.84, 0.74, 0.54, 1.0)
        
    elif preset == "dark_wood":
        # Dark walnut - deep rich browns
        color_ramp.color_ramp.elements[0].color = (0.18, 0.10, 0.05, 1.0)
        color_ramp.color_ramp.elements[1].color = (0.35, 0.20, 0.10, 1.0)
        elem = color_ramp.color_ramp.elements.new(0.3)
        elem.color = (0.22, 0.13, 0.06, 1.0)
        elem = color_ramp.color_ramp.elements.new(0.7)
        elem.color = (0.30, 0.17, 0.08, 1.0)
        
    else:  # "wood" - natural medium brown
        color_ramp.color_ramp.elements[0].color = (0.35, 0.20, 0.10, 1.0)
        color_ramp.color_ramp.elements[1].color = (0.55, 0.35, 0.20, 1.0)
        elem = color_ramp.color_ramp.elements.new(0.3)
        elem.color = (0.40, 0.24, 0.12, 1.0)
        elem = color_ramp.color_ramp.elements.new(0.7)
        elem.color = (0.50, 0.32, 0.17, 1.0)


def _configure_wood_bsdf(bsdf: bpy.types.ShaderNodeBsdfPrincipled, preset: str):
    """Configure BSDF parameters based on wood preset.
    
    Uses Blender 4.0+ compatible input names with fallback for older versions.
    """
    def set_bsdf_input(bsdf, name, value):
        """Safely set BSDF input if it exists."""
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = value
    
    # Blender 4.0+ uses "Coat Weight" instead of "Clearcoat"
    # and "Coat Roughness" instead of "Clearcoat Roughness"
    coat_weight_name = 'Coat Weight' if 'Coat Weight' in bsdf.inputs else 'Clearcoat'
    coat_roughness_name = 'Coat Roughness' if 'Coat Roughness' in bsdf.inputs else 'Clearcoat Roughness'
    
    if preset == "light_wood":
        bsdf.inputs['Metallic'].default_value = 0.0
        bsdf.inputs['Roughness'].default_value = 0.55
        bsdf.inputs['Specular IOR Level'].default_value = 0.3
        set_bsdf_input(bsdf, coat_weight_name, 0.1)
        set_bsdf_input(bsdf, coat_roughness_name, 0.1)
        
    elif preset == "dark_wood":
        bsdf.inputs['Metallic'].default_value = 0.0
        bsdf.inputs['Roughness'].default_value = 0.5
        bsdf.inputs['Specular IOR Level'].default_value = 0.4
        set_bsdf_input(bsdf, coat_weight_name, 0.2)
        set_bsdf_input(bsdf, coat_roughness_name, 0.05)
        
    else:  # "wood" - natural medium
        bsdf.inputs['Metallic'].default_value = 0.0
        bsdf.inputs['Roughness'].default_value = 0.5
        bsdf.inputs['Specular IOR Level'].default_value = 0.35
        set_bsdf_input(bsdf, coat_weight_name, 0.15)
        set_bsdf_input(bsdf, coat_roughness_name, 0.1)
    
    # Common settings for all wood
    bsdf.inputs['IOR'].default_value = 1.5


def apply_material_to_object(obj: bpy.types.Object, preset: str):
    """
    Apply wood material to an object.
    
    Args:
        obj: Target object
        preset: Wood preset name
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    if not obj or obj.type != 'MESH':
        return False, f"Object '{obj.name if obj else 'None'}' is not a mesh"
    
    mat = get_or_create_wood_material(preset)
    
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    
    return True, f"Applied '{WOOD_MATERIAL_NAMES[preset]}' to '{obj.name}'"


def apply_material_to_selected(preset: str):
    """
    Apply wood material to all selected mesh objects.
    
    Args:
        preset: Wood preset name
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    selected_meshes = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    
    if not selected_meshes:
        return False, "No selected mesh objects"
    
    mat = get_or_create_wood_material(preset)
    
    for obj in selected_meshes:
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
    
    return True, f"Applied '{WOOD_MATERIAL_NAMES[preset]}' to {len(selected_meshes)} object(s)"


def get_active_object_or_error():
    """Get the active object or return error tuple."""
    obj = bpy.context.active_object
    if not obj:
        return None, "No active object. Select an object first."
    if obj.type != 'MESH':
        return None, f"Active object '{obj.name}' is not a mesh"
    return obj, None


def validate_wood_preset(preset: str) -> str:
    """Validate wood preset and return normalized name."""
    if preset not in SUPPORTED_WOOD_PRESETS:
        # Handle common aliases
        aliases = {
            "oak": "light_wood",
            "beech": "light_wood",
            "maple": "light_wood",
            "walnut": "dark_wood",
            "mahogany": "dark_wood",
            "cherry": "dark_wood",
            "natural": "wood",
            "medium": "wood",
        }
        if preset in aliases:
            return aliases[preset]
        raise ValueError(f"Unsupported wood preset: {preset}. Supported: {list(SUPPORTED_WOOD_PRESETS)}")
    return preset