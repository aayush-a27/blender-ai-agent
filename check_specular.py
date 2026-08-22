import sys
sys.path.insert(0, '.')
with open('materials/procedural.py') as fp:
    content = fp.read()

# Check for old Specular
if "'Specular'" in content:
    print('ERROR: Old Specular still found')
else:
    print('OK: Old Specular replaced')

# Verify all bsdf inputs
for i, line in enumerate(content.split('\n'), 1):
    if 'bsdf.inputs' in line:
        print('  Line {}: {}'.format(i, line.strip()))