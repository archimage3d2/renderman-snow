# RenderMan Snow — Blender Addon

**Author:** Mark Flanagan  

A Blender addon that adds physically-based, world-normal-driven snow accumulation to any RenderMan LaMA material. No OSL required — built entirely from native RenderMan 27.1 nodes.

![Snow Shader](docs/preview.png)

## Features

- **Non-destructive** — inserts over any existing LaMA material graph, fully removable
- **Live controls** — all parameters drive the node graph in real time via the N-panel
- **Pure RenderMan nodes** — no OSL compile step, single `.py` file install
- **LaMA-native** — uses `LamaMix`, `LamaLayer`, `LamaDiffuse`, `LamaSSS`, `LamaSheenBxdf`
- **World-space mask** — `PxrVariable(Nn)` + `PxrDot` + `PxrThreshold` for clean orientation-based accumulation
- **Organic edge** — fractal noise multiplied into the mask (not mixed) so vertical faces stay clean
- **Optional displacement** — `PxrDisplace` driven by the same mask

## Requirements

| Component | Version |
|---|---|
| Blender | 4.0+ |
| RenderMan for Blender (rfb) | 27.1+ |
| RenderMan | 27.1+ |

## Installation

1. Download `renderman_snow.py`
2. In Blender: **Edit > Preferences > Add-ons > Install**
3. Select `renderman_snow.py`
4. Enable **RenderMan Snow (LaMA)**

> **Important:** Always use **Remove** before reinstalling an update — do not just untick and retick the checkbox, as Blender caches the old file.

## Usage

1. Select a mesh object with an existing RenderMan LaMA material
2. Set the renderer to **RenderMan**
3. Open the **N-panel** (press `N`) > **RenderMan Snow** tab
4. Click **Add Snow Material**
5. Adjust sliders live

## Parameters

### Snow Mask
| Parameter | Description |
|---|---|
| Threshold | Minimum upward-facing angle to receive snow. 0 = all faces, 1 = flat tops only |
| Falloff | Edge sharpness. Higher = harder snow line |

### Edge Noise
| Parameter | Description |
|---|---|
| Noise Amount | How much fractal noise breaks up the edge |
| Noise Frequency | World-space scale of the noise |
| Noise Octaves | Fractal detail layers |
| Noise Distortion | Warps the noise for organic irregularity |
| Noise Contrast | Sharpens or softens the noise pattern |

### Snow Appearance
| Parameter | Description |
|---|---|
| Snow Color | Base diffuse colour (default: cool blue-white) |
| Roughness | Surface roughness (0.85 = packed snow) |
| SSS Weight | Subsurface scatter — simulates packed ice crystals |
| SSS Color | Subsurface colour (default: blue tint) |
| Sheen Weight | Surface sparkle / glint |

### Displacement
| Parameter | Description |
|---|---|
| Enable Displacement | Drives `PxrDisplace` with the snow mask |
| Snow Depth | Maximum displacement in scene units |

> **Note:** Displacement requires a Subdivision Surface modifier on the mesh and a Displacement Bound set in **Object Properties > RenderMan**.

## Node Graph

```
PxrVariable(Nn) ──► PxrDot ──► PxrThreshold ──► PxrArithmetic(multiply)
                                                         ▲
PxrFractal ──► PxrGamma(contrast) ───────────────────────┘
                                         │
                                         ▼
                                   LamaMix.mix
                                   ├── material1: existing base material
                                   └── material2: LamaLayer
                                                   ├── LamaDiffuse (snow)
                                                   ├── LamaSSS
                                                   └── LamaSheen
                                         │
                                         ▼
                                   RendermanOutputNode
                                         │
                                   PxrDisplace (optional)
```

## Removing Snow

Click **Clear Snow Nodes** in the panel. The original material connection is automatically restored.

## Known Limitations

- Designed for LaMA-based materials. Works with `PxrSurface` materials but the base will appear as a plain LamaDiffuse placeholder rather than the original PxrSurface shading.
- Displacement requires manual setup of subdivision and displacement bound on the object.
- Scene properties (`sn_threshold` etc.) are stored on the Blender Scene, so values are shared across all objects in the scene.

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## License

MIT License — see [LICENSE](LICENSE)
