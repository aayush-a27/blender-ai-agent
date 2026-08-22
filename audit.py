import sys
sys.path.insert(0, '.')
with open('materials/procedural.py') as fp:
    content = fp.read()

# Check for problematic patterns
if "'Specular'" in content:
    print('WARNING: Old Specular found')
else:
    print('OK: Old Specular removed')
if "'Clearcoat'" in content and 'Coat Weight' not in content:
    print('WARNING: Clearcoat without Coat Weight fallback')
else:
    print('OK: Clearcoat handled with fallback')
if 'noise_type' in content:
    print('WARNING: noise_type still present')
else:
    print('OK: noise_type removed')

# Check all required links
required_links = [
    'Base Color',
    'Normal',
    'Roughness',
    'BSDF',
    'Surface'
]
for link in required_links:
    if link in content:
        print('OK: {} link/connection found'.format(link))
    else:
        print('MISSING: {}'.format(link))

# Verify node connections
print()
print('Node connection audit:')
connections = [
    ("Generated -> Mapping Vector", "Generated'], mapping.inputs['Vector']"),
    ("Mapping -> Noise 1", "mapping.outputs['Vector'], noise_1.inputs['Vector']"),
    ("Mapping -> Noise 2", "mapping.outputs['Vector'], noise_2.inputs['Vector']"),
    ("Mapping -> Wave", "mapping.outputs['Vector'], wave_tex.inputs['Vector']"),
    ("Noise 1 -> ColorRamp 1", "noise_1.outputs['Fac'], color_ramp_1.inputs['Fac']"),
    ("Wave -> ColorRamp 2", "wave_tex.outputs['Fac'], color_ramp_2.inputs['Fac']"),
    ("ColorRamp 2 -> Bump", "color_ramp_2.outputs['Color'], bump.inputs['Height']"),
    ("ColorRamp 1 -> Mix", "color_ramp_1.outputs['Color'], mix_rgb.inputs['Color1']"),
    ("ColorRamp 2 -> Mix", "color_ramp_2.outputs['Color'], mix_rgb.inputs['Color2']"),
    ("Mix -> Base Color", "mix_rgb.outputs['Color'], bsdf.inputs['Base Color']"),
    ("Bump -> Normal", "bump.outputs['Normal'], bsdf.inputs['Normal']"),
    ("Noise 2 -> Roughness", "noise_2.outputs['Fac'], bsdf.inputs['Roughness']"),
    ("BSDF -> Surface", "bsdf.outputs['BSDF'], output.inputs['Surface']"),
]
for name, pattern in connections:
    if pattern in content:
        print('  OK: {}'.format(name))
    else:
        print('  MISSING: {}'.format(name))