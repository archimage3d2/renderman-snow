# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [3.3.0] — 2026-04-27

### Fixed
- Noise bleed on vertical faces — replaced `PxrMix` with `PxrArithmetic(multiply)`
  so noise is strictly contained within the threshold mask
- Displacement connection — `displace_out` now correctly wires to `displace_in`

### Added
- Noise Octaves slider (`PxrFractal.lacunarity`)
- Noise Distortion slider (`PxrFractal.erosion`)
- Noise Contrast slider (`Sn_NoiseGamma.gamma`)
- `Sn_NoiseGamma` node between fractal and multiply for contrast control

---

## [3.2.0] — 2026-04-27

### Added
- Version display in N-panel showing version number and load time
- `_find_existing_bxdf` now walks past existing `Sn_` nodes when re-applying snow

### Fixed
- Clear operator now restores original material connection using stored metadata
  (`mat['sn_original_node']`, `mat['sn_original_socket']`)
- Clear operator no longer wipes entire material — only removes `Sn_` prefixed nodes

---

## [3.1.0] — 2026-04-27

### Changed
- Properties moved from `PropertyGroup` to direct `bpy.types.Scene` registration
  for reliable `update=` callback firing
- All sliders now live-drive the node graph without requiring **Add Snow Material**
  to be clicked again

### Fixed
- Update callbacks were receiving `Scene` as `self` rather than `PropertyGroup` —
  all callbacks now use `context.scene.sn_*` directly

---

## [3.0.0] — 2026-04-27

### Changed
- Complete rewrite — pure RenderMan nodes, no OSL
- Replaced `PxrRemap` + `PxrGamma` threshold chain with `PxrThresholdPatternNode`
- Replaced `PxrAttributePatternNode` with `PxrVariablePatternNode` for world-space normal
- `LamaSurfaceBxdfNode` removed — `LamaMix` connects directly to output
- Up vector set via `PxrDot.vector2` node property (Z-up in RenderMan world space)
- Deferred timer pass ensures rfb node initialisation doesn't overwrite property values
- All node labels prefixed `Sn_` for easy identification

### Fixed
- All socket names verified against live rfb 27.1 inspection
- Color assignments use 3-component tuples
- Node property assignment uses direct `node.prop = value` pattern

---

## [2.0.0] — 2026-04-27

### Changed
- Removed OSL dependency — no compile step required
- Single file install

---

## [1.0.0] — 2026-04-27

### Added
- Initial release with OSL `SnowMask.osl` shader
- Blender addon with LaMA node graph builder
- N-panel UI with threshold, falloff, SSS, sheen, displacement controls
