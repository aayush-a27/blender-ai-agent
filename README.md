# Blender AI Agent - V1.5

A professional Blender addon for AI-powered 3D modeling using NVIDIA Nemotron 3 Ultra.

## Features

### V1 (Manual Operations)
- Create Cube, Sphere, Cylinder at 3D cursor
- Delete selected objects
- Clear entire scene
- Custom panel in 3D View Sidebar

### V1.5 (AI-Powered)
- Natural language commands via NVIDIA Nemotron 3 Ultra
- Structured JSON response validation (no arbitrary code execution)
- Secure API key storage in Blender preferences
- Status feedback in UI

## Installation

1. **Download/Clone** this repository
2. **Open Blender** (4.0+)
3. Go to **Edit > Preferences > Add-ons**
4. Click **Install...** and select the `blender-ai-agent` folder (or zip it first)
5. Enable the checkbox for **Blender AI Agent**
6. Press **N** in the 3D Viewport to open the Sidebar
7. Click the **Blender AI Agent** tab

## API Key Configuration

**Required for AI features:**

1. Get an API key from [NVIDIA Build](https://build.nvidia.com)
2. In Blender: **Edit > Preferences > Add-ons > Blender AI Agent**
3. Expand the addon preferences and paste your **NVIDIA API Key**
4. (Optional) Adjust model, endpoint, max tokens, temperature

The API key is stored in Blender's user preferences, **never in source code**.

Alternative: Set `NVIDIA_API_KEY` environment variable before starting Blender.

## Usage

### Manual Buttons (V1)
Use the "Create Objects" and "Modify Scene" buttons as before.

### AI Commands (V1.5)
1. Type a command in the **AI Command** text field
2. Click **Execute**
3. Watch the status: `Sending...` → `Processing...` → `Executing...` → `Completed`

**Supported commands:**
| Command | Action |
|---------|--------|
| `Create a cube` | Creates a cube at origin |
| `Create a red cube` | Creates a red cube |
| `Create a sphere at 2, 0, 0` | Creates sphere at location |
| `Create a blue cylinder at 1, 2, 3 with scale 2` | Creates cylinder with params |
| `Delete selected` | Deletes selected objects |
| `Clear the scene` | Deletes all objects |

**Unsupported (returns error):**
- `Move the cube left` - Transform ops not in V1.5
- `Create a character` - Complex generation not in V1.5

## Architecture

```
blender-ai-agent/
├── __init__.py          # Addon metadata, registration
├── operators.py         # Blender operators (manual + AI)
├── panels.py            # UI panel (Sidebar)
├── properties.py        # Properties + AddonPreferences (API key)
├── utils.py             # Helper functions
├── ai/
│   ├── __init__.py
│   ├── client.py        # NVIDIA API communication
│   ├── prompts.py       # System prompt for Nemotron
│   └── actions.py       # JSON validation + Blender execution
├── .gitignore
└── README.md
```

### Security: No Arbitrary Code Execution

1. Nemotron returns **only JSON** (strict system prompt)
2. Addon **validates** JSON against strict schema
3. Only **predefined actions** execute via trusted Blender functions
4. **NO** `exec()`, `eval()`, or dynamic code execution

Example AI response:
```json
{
  "action": "create_object",
  "object_type": "cube",
  "location": [0, 0, 0],
  "scale": [1, 1, 1],
  "color": [1, 0, 0, 1]
}
```

## Development

### Testing Changes
After modifying code:
1. Disable addon in Preferences
2. Enable addon again (reloads Python modules)
3. Or press **F8** in Blender's Text Editor with `__init__.py` open

### Key Concepts
- **`bpy`**: Blender's Python API
- **`bpy.ops`**: Built-in operators (e.g., `bpy.ops.mesh.primitive_cube_add()`)
- **Operator**: Class with `execute()` that performs an action
- **Panel**: Class with `draw()` that creates UI
- **AddonPreferences**: Persistent user settings (API key stored here)
- **`register()`/`unregister()`**: Called by Blender on enable/disable

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API key not configured" | Set key in Preferences > Add-ons > Blender AI Agent |
| "Network error" | Check internet connection, verify endpoint URL |
| "Invalid AI response" | Model returned malformed JSON; try rephrasing command |
| "Unsupported action" | Command not in V1.5 scope; use manual buttons |
| Panel not showing | Ensure addon enabled, press N in 3D Viewport |

## Security Notes

- API key stored in Blender preferences (not in repo)
- `.gitignore` excludes local config
- No secrets in logs, errors, or UI
- No arbitrary code execution from AI responses

## Future (V2+)

- Multi-step agent loops
- Complex scene generation
- Material/texture control
- Transform operations (move, rotate, scale)
- Memory/context across commands

## License

MIT