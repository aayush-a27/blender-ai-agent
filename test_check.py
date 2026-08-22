import sys
sys.path.insert(0, '.')

with open('ai/actions.py') as f:
    content = f.read()

# Check create_light in SUPPORTED_ACTIONS
if 'create_light' in content:
    print('create_light in source: PASS')
else:
    print('create_light in source: FAIL')
    sys.exit(1)

# Check _validate_create_light exists
if '_validate_create_light' in content:
    print('_validate_create_light function: PASS')
else:
    print('_validate_create_light function: FAIL')
    sys.exit(1)

# Check elif branch for create_light
if 'elif action == "create_light":' in content:
    print('elif create_light branch: PASS')
else:
    print('elif create_light branch: FAIL')
    sys.exit(1)

# Check dispatcher has create_light branch
if 'elif action_type == "create_light":' in content:
    print('dispatcher create_light branch: PASS')
else:
    print('dispatcher create_light branch: FAIL')
    sys.exit(1)

print()
print('All structural checks PASSED!')