"""
renderman_snow.py  -  Blender Addon  v3
========================================
LaMA snow using pure RenderMan nodes - no OSL, single file install.
Panel sliders live-drive the node graph via direct Scene properties.

Install:  Edit > Preferences > Add-ons > Install > enable
Use:      N-panel > RenderMan Snow > Add Snow Material
"""

bl_info = {
    "name":        "RenderMan Snow (LaMA)",
    "author":      "Mark Flanagan",
    "version":     (3, 3, 0),
    "blender":     (4, 0, 0),
    "location":    "N-Panel > RenderMan Snow",
    "description": "World-normal LaMA snow - pure RenderMan nodes, no OSL",
    "category":    "Render",
}

import bpy
import datetime
from bpy.types import Operator, Panel
from bpy.props import FloatProperty, BoolProperty, FloatVectorProperty

ADDON_VERSION = "v3.3.0"
_LOAD_TIME = datetime.datetime.now().strftime('%H:%M:%S')


# ─────────────────────────────────────────────────────────────────────────────
# Node finder
# ─────────────────────────────────────────────────────────────────────────────

def _get_snow_nodes(context):
    obj = getattr(context, 'active_object', None)
    if not obj or not getattr(obj, 'active_material', None):
        return {}
    nt = obj.active_material.node_tree
    if not nt:
        return {}
    return {n.name: n for n in nt.nodes if n.name.startswith('Sn_')}


# ─────────────────────────────────────────────────────────────────────────────
# Update callbacks — defined at module level, registered on Scene directly
# ─────────────────────────────────────────────────────────────────────────────

def _upd_threshold(self, context):
    print(f"[Snow] _upd_threshold fired, self type={type(self).__name__}, val={self.sn_threshold}")
    nodes = _get_snow_nodes(context)
    print(f"[Snow] nodes found: {list(nodes.keys())}")
    n = nodes.get('Sn_Threshold')
    if n:
        n.threshold       = self.sn_threshold
        n.transitionWidth = max(0.001, (1.0 - self.sn_threshold) / self.sn_falloff)
        print(f"[Snow] Set OK: threshold={n.threshold}")
    else:
        print("[Snow] Sn_Threshold NOT found")

def _upd_falloff(self, context):
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_Threshold')
    if n:
        n.transitionWidth = max(0.001, (1.0 - self.sn_threshold) / self.sn_falloff)

def _upd_noise_amount(self, context):
    # noise amount scales the noise gamma brightness before multiply
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_NoiseGamma')
    if n:
        # Higher amount = more noise influence — drive via gamma
        # gamma < 1 brightens (more noise), gamma > 1 darkens (less noise)
        # Map 0-1 amount to gamma range 4.0 (subtle) to 0.3 (heavy)
        import bpy
        amount = bpy.context.scene.sn_noise_amount
        n.gamma = max(0.1, 4.0 - (amount * 3.7))

def _upd_noise_frequency(self, context):
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_Noise')
    if n:
        n.frequency = self.sn_noise_frequency

def _upd_snow_color(self, context):
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_Diffuse')
    if n:
        n.diffuseColor[0] = self.sn_snow_color[0]
        n.diffuseColor[1] = self.sn_snow_color[1]
        n.diffuseColor[2] = self.sn_snow_color[2]

def _upd_snow_roughness(self, context):
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_Diffuse')
    if n:
        n.roughness = self.sn_snow_roughness

def _upd_sss_weight(self, context):
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_SSS')
    if n:
        n.sssScale = self.sn_sss_weight
    layer = nodes.get('Sn_Layer')
    if layer:
        layer.topMix = self.sn_sss_weight

def _upd_sss_color(self, context):
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_SSS')
    if n:
        n.sssColor[0] = self.sn_sss_color[0]
        n.sssColor[1] = self.sn_sss_color[1]
        n.sssColor[2] = self.sn_sss_color[2]

def _upd_sheen_weight(self, context):
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_Sheen')
    if n:
        sv = self.sn_sheen_weight
        n.sheenColor[0] = sv
        n.sheenColor[1] = sv
        n.sheenColor[2] = sv
    layer = nodes.get('Sn_SheenLayer')
    if layer:
        layer.topMix = self.sn_sheen_weight

def _upd_noise_octaves(self, context):
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_Noise')
    if n:
        n.lacunarity = self.sn_noise_octaves

def _upd_noise_distortion(self, context):
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_Noise')
    if n:
        n.erosion = self.sn_noise_distortion

def _upd_noise_contrast(self, context):
    nodes = _get_snow_nodes(context)
    # Use a PxrGamma on the noise output to control contrast
    n = nodes.get('Sn_NoiseGamma')
    if n:
        n.gamma = self.sn_noise_contrast

def _upd_displacement_depth(self, context):
    nodes = _get_snow_nodes(context)
    n = nodes.get('Sn_Displace')
    if n:
        n.dispAmount = self.sn_displacement_depth


# ─────────────────────────────────────────────────────────────────────────────
# Node helpers
# ─────────────────────────────────────────────────────────────────────────────

def _node(nt, bl_type, label, pos):
    try:
        n = nt.nodes.new(bl_type)
    except RuntimeError:
        print(f"[SnowAddon] Node type not found: {bl_type}")
        return None
    n.label    = label
    n.name     = label
    n.location = pos
    return n


def _link(nt, src, src_sock, dst, dst_sock):
    if src is None or dst is None:
        return
    try:
        nt.links.new(src.outputs[src_sock], dst.inputs[dst_sock])
    except (KeyError, IndexError) as e:
        print(f"[SnowAddon] Link skipped ({src.label}:{src_sock} -> {dst.label}:{dst_sock}): {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────────────────────────────────────

def _find_rm_output(nt):
    for n in nt.nodes:
        if n.bl_idname == 'RendermanOutputNode':
            return n
    return None


def _find_existing_bxdf(nt, rm_out):
    try:
        bxdf_input = rm_out.inputs['bxdf_in']
    except KeyError:
        return None, None
    if not bxdf_input.is_linked:
        return None, None
    link = bxdf_input.links[0]
    node = link.from_node
    # If the connected node is already a snow node, walk back through
    # material1 to find the real original base material
    if node.name.startswith('Sn_'):
        try:
            mat1 = node.inputs['material1']
            if mat1.is_linked:
                orig = mat1.links[0]
                return orig.from_node, orig.from_socket.name
        except KeyError:
            pass
        return None, None
    return node, link.from_socket.name


def build_snow_graph(mat, scene):
    mat.use_nodes = True
    nt = mat.node_tree

    rm_out = _find_rm_output(nt)
    if rm_out is None:
        rm_out = _node(nt, 'RendermanOutputNode', "RM_Output", (600, 0))

    existing_bxdf, existing_socket = _find_existing_bxdf(nt, rm_out)
    ox, oy = rm_out.location.x, rm_out.location.y

    # Store original bxdf connection so clear operator can restore it
    if existing_bxdf:
        mat['sn_original_node']   = existing_bxdf.name
        mat['sn_original_socket'] = existing_socket
    else:
        mat['sn_original_node']   = ""
        mat['sn_original_socket'] = ""
    print(f"[SnowAddon] Stored original: {mat.get('sn_original_node')} : {mat.get('sn_original_socket')}")

    # ── 1. World normal via PxrVariable ──────────────────────────────────────
    attr_n = _node(nt, 'PxrVariablePatternNode', "Sn_Attr_Nn",
                   (ox - 900, oy + 500))
    if attr_n:
        attr_n.variable  = "Nn"
        attr_n.rman_type = "normal"
        attr_n.coordsys  = "world"

    # ── 2. PxrDot — dot(normal, world-Z) ─────────────────────────────────────
    dot = _node(nt, 'PxrDotPatternNode', "Sn_Dot",
                (ox - 680, oy + 500))
    if dot and attr_n:
        _link(nt, attr_n, "resultRGB", dot, "vector1")

    # ── 3. PxrThreshold — threshold + soft edge ───────────────────────────────
    thresh = _node(nt, 'PxrThresholdPatternNode', "Sn_Threshold",
                   (ox - 460, oy + 500))
    if thresh and dot:
        _link(nt, dot, "result", thresh, "inputRGB")

    mask_node   = thresh
    mask_socket = "resultR"

    # ── 4. Noise chain — fractal multiplied by threshold mask ────────────────
    # Multiply keeps noise strictly within snowy areas — no bleed on verticals.
    fractal = _node(nt, 'PxrFractalPatternNode', "Sn_Noise",
                    (ox - 680, oy + 300))

    # PxrGamma on fractal controls noise contrast
    noise_gamma = _node(nt, 'PxrGammaPatternNode', "Sn_NoiseGamma",
                        (ox - 460, oy + 300))
    if noise_gamma and fractal:
        _link(nt, fractal, "resultRGB", noise_gamma, "inputRGB")

    # PxrArithmetic multiply: threshold * noise = clean mask, no vertical bleed
    noise_mix = _node(nt, 'PxrArithmeticPatternNode', "Sn_NoiseMix",
                      (ox - 240, oy + 300))
    if noise_mix and thresh and noise_gamma:
        noise_mix.operation = '1'  # Multiply
        _link(nt, thresh,      "resultRGB", noise_mix, "input1")
        _link(nt, noise_gamma, "resultRGB", noise_mix, "input2")
        mask_node   = noise_mix
        mask_socket = "resultR"

    # ── 5. Snow lobes ─────────────────────────────────────────────────────────
    snow_diff = _node(nt, 'LamaDiffuseBxdfNode', "Sn_Diffuse",
                      (ox - 680, oy - 100))

    snow_sss = _node(nt, 'LamaSSSBxdfNode', "Sn_SSS",
                     (ox - 680, oy - 300))

    snow_sheen = _node(nt, 'LamaSheenBxdfNode', "Sn_Sheen",
                       (ox - 680, oy - 500))

    snow_layer = _node(nt, 'LamaLayerBxdfNode', "Sn_Layer",
                       (ox - 460, oy - 200))
    if snow_layer:
        if snow_diff: _link(nt, snow_diff, "bxdf_out", snow_layer, "materialBase")
        if snow_sss:  _link(nt, snow_sss,  "bxdf_out", snow_layer, "materialTop")

    sheen_layer = _node(nt, 'LamaLayerBxdfNode', "Sn_SheenLayer",
                        (ox - 240, oy - 200))
    if sheen_layer:
        if snow_layer:  _link(nt, snow_layer,  "bxdf_out", sheen_layer, "materialBase")
        if snow_sheen:  _link(nt, snow_sheen,  "bxdf_out", sheen_layer, "materialTop")

    snow_top = sheen_layer or snow_layer or snow_diff

    # ── 6. LamaMix ────────────────────────────────────────────────────────────
    lama_mix = _node(nt, 'LamaMixBxdfNode', "Sn_LamaMix",
                     (ox - 50, oy + 100))
    if lama_mix:
        if existing_bxdf:
            _link(nt, existing_bxdf, existing_socket, lama_mix, "material1")
        if snow_top:
            _link(nt, snow_top, "bxdf_out", lama_mix, "material2")
        if mask_node:
            _link(nt, mask_node, mask_socket, lama_mix, "mix")

    # ── 7. Reconnect output ───────────────────────────────────────────────────
    for lnk in list(rm_out.inputs['bxdf_in'].links):
        nt.links.remove(lnk)
    if lama_mix:
        _link(nt, lama_mix, "bxdf_out", rm_out, "bxdf_in")

    rm_out.location.x = max(rm_out.location.x, ox + 450)

    # ── 8. Optional displacement ──────────────────────────────────────────────
    if scene.sn_displacement_enable and mask_node:
        pxr_disp = _node(nt, 'PxrDisplaceDisplaceNode',
                         "Sn_Displace", (ox + 200, oy - 100))
        if pxr_disp:
            _link(nt, mask_node, mask_socket, pxr_disp, "dispScalar")
            _link(nt, pxr_disp, "displace_out", rm_out, "displace_in")

    print("[SnowAddon] Graph built. Running deferred property pass...")

    # ── 9. Deferred property pass ─────────────────────────────────────────────
    mat_name = mat.name

    def apply_props():
        m = bpy.data.materials.get(mat_name)
        if not m:
            return None
        nodes = {n.name: n for n in m.node_tree.nodes if n.name.startswith('Sn_')}

        n = nodes.get('Sn_Dot')
        if n:
            n.vector2[0] = 0.0
            n.vector2[1] = 0.0
            n.vector2[2] = 1.0

        n = nodes.get('Sn_Threshold')
        if n:
            n.threshold       = scene.sn_threshold
            n.transitionWidth = max(0.001, (1.0 - scene.sn_threshold) / scene.sn_falloff)

        n = nodes.get('Sn_Noise')
        if n:
            n.frequency  = scene.sn_noise_frequency
            n.lacunarity = scene.sn_noise_octaves
            n.erosion    = scene.sn_noise_distortion

        n = nodes.get('Sn_NoiseMix')
        if n:
            n.operation = '1'  # Multiply

        n = nodes.get('Sn_NoiseGamma')
        if n:
            n.gamma = scene.sn_noise_contrast

        # noise_mix is now PxrArithmetic multiply — no mixer property
        # noise amount is controlled via Sn_NoiseGamma.gamma
        n = nodes.get('Sn_NoiseGamma')
        if n:
            amount = scene.sn_noise_amount
            n.gamma = max(0.1, 4.0 - (amount * 3.7))

        n = nodes.get('Sn_Diffuse')
        if n:
            n.diffuseColor[0] = scene.sn_snow_color[0]
            n.diffuseColor[1] = scene.sn_snow_color[1]
            n.diffuseColor[2] = scene.sn_snow_color[2]
            n.roughness = scene.sn_snow_roughness

        n = nodes.get('Sn_SSS')
        if n:
            n.sssColor[0] = scene.sn_sss_color[0]
            n.sssColor[1] = scene.sn_sss_color[1]
            n.sssColor[2] = scene.sn_sss_color[2]
            n.sssScale = scene.sn_sss_weight

        n = nodes.get('Sn_Sheen')
        if n:
            sv = scene.sn_sheen_weight
            n.sheenColor[0] = sv
            n.sheenColor[1] = sv
            n.sheenColor[2] = sv

        layer = nodes.get('Sn_Layer')
        if layer:
            layer.topMix = scene.sn_sss_weight

        sl = nodes.get('Sn_SheenLayer')
        if sl:
            sl.topMix = scene.sn_sheen_weight

        n = nodes.get('Sn_Displace')
        if n:
            n.dispAmount = scene.sn_displacement_depth

        print("[SnowAddon] Deferred property pass complete.")
        return None

    bpy.app.timers.register(apply_props, first_interval=0.5)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Operators
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_material(obj):
    if obj.material_slots and obj.material_slots[0].material:
        return obj.material_slots[0].material
    mat = bpy.data.materials.new(name="RM_Snow")
    mat.use_nodes = True
    if not obj.material_slots:
        obj.data.materials.append(mat)
    else:
        obj.material_slots[0].material = mat
    return mat


class SNOW_OT_add(Operator):
    bl_idname      = "renderman_snow.add"
    bl_label       = "Add Snow Material"
    bl_description = "Build a LaMA snow material on the selected object"
    bl_options     = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, ctx):
        return ctx.active_object and ctx.active_object.type == "MESH"

    def execute(self, ctx):
        obj = ctx.active_object
        mat = _get_or_create_material(obj)
        build_snow_graph(mat, ctx.scene)
        self.report({"INFO"}, f"Snow applied to '{obj.name}'")
        return {"FINISHED"}


class SNOW_OT_clear(Operator):
    bl_idname      = "renderman_snow.clear"
    bl_label       = "Clear Snow Nodes"
    bl_description = "Remove Sn_ snow nodes from the active material"
    bl_options     = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, ctx):
        o = ctx.active_object
        return (o and o.type == "MESH"
                and o.material_slots
                and o.material_slots[0].material)

    def execute(self, ctx):
        obj = ctx.active_object
        mat = obj.material_slots[0].material
        nt  = mat.node_tree

        # Restore original bxdf connection using stored metadata
        orig_node_name   = mat.get('sn_original_node', '')
        orig_socket_name = mat.get('sn_original_socket', '')

        if orig_node_name:
            orig_node = nt.nodes.get(orig_node_name)
            rm_out    = None
            for n in nt.nodes:
                if n.bl_idname == 'RendermanOutputNode':
                    rm_out = n
                    break

            if orig_node and rm_out:
                # Remove current bxdf_in links
                for lnk in list(rm_out.inputs['bxdf_in'].links):
                    nt.links.remove(lnk)
                # Restore original
                try:
                    nt.links.new(orig_node.outputs[orig_socket_name],
                                 rm_out.inputs['bxdf_in'])
                    print(f"[SnowAddon] Restored: {orig_node_name} : {orig_socket_name}")
                except Exception as e:
                    print(f"[SnowAddon] Restore failed: {e}")

        # Remove all Sn_ nodes
        to_remove = [n for n in nt.nodes if n.name.startswith("Sn_")]
        for n in to_remove:
            nt.nodes.remove(n)

        # Clean up stored metadata
        for key in ('sn_original_node', 'sn_original_socket'):
            if key in mat:
                del mat[key]

        self.report({"INFO"}, f"Removed {len(to_remove)} snow nodes — original material restored.")
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────────────────────
# Panel
# ─────────────────────────────────────────────────────────────────────────────

class SNOW_PT_npanel(Panel):
    bl_label       = "RenderMan Snow"
    bl_idname      = "SNOW_PT_npanel"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "RenderMan Snow"

    def draw(self, ctx):
        layout = self.layout
        s      = ctx.scene

        # Version display
        row = layout.row()
        row.label(text=f"{ADDON_VERSION}  (loaded {_LOAD_TIME})", icon="INFO")
        layout.separator()

        box = layout.box()
        box.label(text="Snow Mask", icon="MOD_SMOOTH")
        box.prop(s, "sn_threshold", slider=True)
        box.prop(s, "sn_falloff",   slider=True)

        box2 = layout.box()
        box2.prop(s, "sn_noise_enable")
        col = box2.column()
        col.enabled = s.sn_noise_enable
        col.prop(s, "sn_noise_amount",     slider=True)
        col.prop(s, "sn_noise_frequency",  slider=True)
        col.prop(s, "sn_noise_octaves",    slider=True)
        col.prop(s, "sn_noise_distortion", slider=True)
        col.prop(s, "sn_noise_contrast",   slider=True)

        box3 = layout.box()
        box3.label(text="Snow Appearance", icon="FREEZE")
        box3.prop(s, "sn_snow_color")
        box3.prop(s, "sn_snow_roughness", slider=True)

        box3.prop(s, "sn_sss_enable")
        col2 = box3.column()
        col2.enabled = s.sn_sss_enable
        col2.prop(s, "sn_sss_weight", slider=True)
        col2.prop(s, "sn_sss_color")

        box3.prop(s, "sn_sheen_enable")
        col3 = box3.column()
        col3.enabled = s.sn_sheen_enable
        col3.prop(s, "sn_sheen_weight", slider=True)

        box4 = layout.box()
        box4.label(text="Displacement", icon="RNDCURVE")
        box4.prop(s, "sn_displacement_enable")
        col4 = box4.column()
        col4.enabled = s.sn_displacement_enable
        col4.prop(s, "sn_displacement_depth")

        layout.separator()
        layout.operator("renderman_snow.add",   icon="SHADERFX")
        layout.operator("renderman_snow.clear", icon="TRASH")


# ─────────────────────────────────────────────────────────────────────────────
# Registration — properties go directly on Scene for reliable update callbacks
# ─────────────────────────────────────────────────────────────────────────────

classes = (SNOW_OT_add, SNOW_OT_clear, SNOW_PT_npanel)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.sn_threshold = FloatProperty(
        name="Threshold", default=0.5, min=0.0, max=0.99,
        step=1, precision=2, update=_upd_threshold,
        description="Minimum upward facing to receive snow",
    )
    bpy.types.Scene.sn_falloff = FloatProperty(
        name="Falloff", default=3.0, min=0.1, max=20.0,
        step=10, precision=1, update=_upd_falloff,
        description="Edge sharpness. Higher = harder snow line",
    )
    bpy.types.Scene.sn_noise_enable = BoolProperty(
        name="Edge Noise", default=True,
    )
    bpy.types.Scene.sn_noise_amount = FloatProperty(
        name="Noise Amount", default=0.3, min=0.0, max=1.0,
        step=1, precision=2, update=_upd_noise_amount,
    )
    bpy.types.Scene.sn_noise_frequency = FloatProperty(
        name="Noise Frequency", default=3.0, min=0.01, max=20.0,
        step=10, precision=1, update=_upd_noise_frequency,
    )
    bpy.types.Scene.sn_snow_color = FloatVectorProperty(
        name="Snow Color", subtype="COLOR", size=3,
        default=(0.92, 0.95, 1.0), min=0.0, max=1.0,
        update=_upd_snow_color,
    )
    bpy.types.Scene.sn_snow_roughness = FloatProperty(
        name="Roughness", default=0.85, min=0.0, max=1.0,
        step=1, precision=2, update=_upd_snow_roughness,
    )
    bpy.types.Scene.sn_sss_enable = BoolProperty(name="Enable SSS", default=True)
    bpy.types.Scene.sn_sss_weight = FloatProperty(
        name="SSS Weight", default=0.25, min=0.0, max=1.0,
        step=1, precision=2, update=_upd_sss_weight,
    )
    bpy.types.Scene.sn_sss_color = FloatVectorProperty(
        name="SSS Color", subtype="COLOR", size=3,
        default=(0.75, 0.88, 1.0), min=0.0, max=1.0,
        update=_upd_sss_color,
    )
    bpy.types.Scene.sn_sheen_enable = BoolProperty(name="Enable Sheen", default=True)
    bpy.types.Scene.sn_sheen_weight = FloatProperty(
        name="Sheen Weight", default=0.15, min=0.0, max=1.0,
        step=1, precision=2, update=_upd_sheen_weight,
    )
    bpy.types.Scene.sn_noise_octaves = FloatProperty(
        name="Octaves", default=2.0, min=0.0, max=8.0,
        step=10, precision=1, update=_upd_noise_octaves,
        description="Number of fractal detail layers",
    )
    bpy.types.Scene.sn_noise_distortion = FloatProperty(
        name="Distortion", default=0.0, min=0.0, max=2.0,
        step=1, precision=2, update=_upd_noise_distortion,
        description="Warps the noise for a more organic look",
    )
    bpy.types.Scene.sn_noise_contrast = FloatProperty(
        name="Contrast", default=1.0, min=0.1, max=5.0,
        step=10, precision=1, update=_upd_noise_contrast,
        description="Sharpens or softens the noise pattern",
    )
    bpy.types.Scene.sn_displacement_enable = BoolProperty(
        name="Enable Displacement", default=False,
    )
    bpy.types.Scene.sn_displacement_depth = FloatProperty(
        name="Snow Depth", default=0.02, min=0.0, max=1.0,
        step=0.1, precision=3, update=_upd_displacement_depth,
    )
    print(f"[SnowAddon] {ADDON_VERSION} registered at {_LOAD_TIME}")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    props = [
        'sn_threshold','sn_falloff','sn_noise_enable','sn_noise_amount',
        'sn_noise_frequency','sn_noise_octaves','sn_noise_distortion','sn_noise_contrast',
        'sn_snow_color','sn_snow_roughness',
        'sn_sss_enable','sn_sss_weight','sn_sss_color',
        'sn_sheen_enable','sn_sheen_weight',
        'sn_displacement_enable','sn_displacement_depth',
    ]
    for p in props:
        if hasattr(bpy.types.Scene, p):
            delattr(bpy.types.Scene, p)
    print("[SnowAddon v3] Unregistered.")


if __name__ == "__main__":
    register()
