"""kais-blender-layout — Blender 场景布局引擎

一句话生成 Blender 场景参考图。
Linux → HTTP POST → Windows Blender 5.1 Cycles GPU。

用法:
    from blender_layout import render_scene
    script = render_scene(
        characters=[{"animation": "...", "position": "sofa"}],
        hdri="kloppenheim_06_4k",
        sofa_scale=1.34,
    )
    # POST /run/script with {"script": script, "timeout": 300}
"""

from typing import Dict, List, Optional, Tuple


# ── 相机预设 ──────────────────────────────────────────────────

CAMERA_PRESETS: Dict[str, Tuple[float, float, float]] = {
    "extreme_wide":      (-4.5, -4.5, 2.8),
    "wide":              (-3.5, -3.5, 2.5),
    "medium":            (-2.0, -2.5, 1.8),
    "closeup":           (-1.2, -1.6, 1.3),
    "extreme_closeup":   (-0.8, -1.0, 1.0),
    "otw_over_shoulder": (-1.0, -1.2, 1.1),
}

# ── 默认配置 ──────────────────────────────────────────────────

DEFAULTS = {
    "base_scene": r"D:\BlenderAgent\cache\full_scene.blend",
    "output_dir": r"D:\BlenderAgent\outputs",
    "hdri_dir": r"D:\BlenderAgent\assets\polyhaven\hdris",
    "samples": 128,
    "resolution": (1280, 720),
    "sofa_scale": 1.34,      # Poly Haven sofa_02 太小，需要放大
    "default_clearance": 0.05,
}


def render_scene(
    characters: List[Dict],
    hdri: str = "kloppenheim_06_4k",
    camera_shots: List[str] = None,
    sofa_scale: float = None,
    output_dir: str = None,
    samples: int = None,
    resolution: Tuple[int, int] = None,
    base_scene: str = None,
) -> str:
    """
    生成完整的 Blender 场景布局脚本。

    Args:
        characters: 角色列表，每个包含:
            - animation: FBX 路径（必填）
            - position: 家具关键词，如 "sofa"（可选）
            - clearance: 与表面的间隙，默认 0.05（可选）
            - scale: 家具缩放倍数（可选）
        hdri: HDRI 文件名（不含路径），默认 kloppenheim_06_4k
        camera_shots: 镜头列表，默认 ["wide", "medium", "closeup"]
        sofa_scale: 沙发缩放倍数，默认 1.34
        output_dir: 输出目录
        samples: 渲染采样数
        resolution: (宽, 高)
        base_scene: 基础场景文件路径

    Returns:
        完整的 Blender Python 脚本字符串
    """
    if camera_shots is None:
        camera_shots = ["wide", "medium", "closeup"]
    sofa_scale = sofa_scale or DEFAULTS["sofa_scale"]
    output_dir = output_dir or DEFAULTS["output_dir"]
    samples = samples or DEFAULTS["samples"]
    resolution = resolution or DEFAULTS["resolution"]
    base_scene = base_scene or DEFAULTS["base_scene"]
    rx, ry = resolution

    # 构建 character blocks
    char_blocks = []
    for ch in characters:
        char_blocks.append({
            "anim": ch.get("animation", ""),
            "target": ch.get("position", "").replace("on:", "").strip(),
            "clearance": ch.get("clearance", DEFAULTS["default_clearance"]),
            "scale": ch.get("scale", sofa_scale),
        })

    L = []  # script lines
    a = L.append

    # ═══ Header ═══
    a("import bpy, sys, mathutils")
    a("sys.stderr.write('[blender-layout] Starting...\\\\n')")

    # ═══ Helpers ═══
    a("def get_aabb(obj):")
    a("    cs = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]")
    a("    xs=[c.x for c in cs]; ys=[c.y for c in cs]; zs=[c.z for c in cs]")
    a("    return mathutils.Vector((min(xs),min(ys),min(zs))), mathutils.Vector((max(xs),max(ys),max(zs)))")
    a("")
    a("def scene_aabb(exclude={'Floor'}):")
    a("    mn=mx=None")
    a("    for o in bpy.context.scene.objects:")
    a("        if o.type in ('MESH','ARMATURE') and o.name not in exclude:")
    a("            a,b=get_aabb(o)")
    a("            if mn is None: mn,mx=a,b")
    a("            else:")
    a("                mn=mathutils.Vector((min(mn.x,a.x),min(mn.y,a.y),min(mn.z,a.z)))")
    a("                mx=mathutils.Vector((max(mx.x,b.x),max(mx.y,b.y),max(mx.z,b.z)))")
    a("    return mn,mx")
    a("")
    a("def look_at(cam, target):")
    a("    d=mathutils.Vector(target)-cam.location")
    a("    cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()")
    a("")

    # ═══ Open base scene ═══
    a(f"bpy.ops.wm.open_mainfile(filepath=r'{base_scene}')")
    a("sys.stderr.write('[blender-layout] Scene loaded\\\\n')")

    # ═══ Scale sofa ═══
    a("# ── Scale sofa to match character proportions ──")
    a(f"sofa_scale = {sofa_scale}")
    a("for obj in bpy.context.scene.objects:")
    a("    if obj.type=='MESH' and 'sofa_02' in obj.name.lower():")
    a("        obj.scale = (sofa_scale, sofa_scale, sofa_scale)")
    a("bpy.context.view_layer.update()")
    a("")
    # ═══ Assemble sofa: seat cushion onto base top ═══
    a("# ── Assemble sofa components ──")
    a("base=next((o for o in bpy.context.scene.objects if o.type=='MESH' and 'sofa_02_base' in o.name.lower()),None)")
    a("seat=next((o for o in bpy.context.scene.objects if o.type=='MESH' and 'sofa_02_seat' in o.name.lower()),None)")
    a("if base and seat:")
    a("    b_mn,b_mx=get_aabb(base); s_mn,s_mx=get_aabb(seat)")
    a("    if s_mn.z < b_mx.z - 0.01:")
    a("        seat.location.z += b_mx.z - s_mn.z")
    a("        bpy.context.view_layer.update()")
    a(f"        sys.stderr.write(f'  Assembled seat onto base\\\\n')")
    a("")

    # ═══ Characters ═══
    for ci, cb in enumerate(char_blocks):
        anim = cb["anim"]
        target = cb["target"]
        clr = cb["clearance"]
        scl = cb["scale"]

        a(f"# ── Character {ci+1} ──")

        # Clean old characters
        a("for obj in list(bpy.context.scene.objects):")
        a("    if obj.type=='ARMATURE' or obj.name=='Human':")
        a("        bpy.data.objects.remove(obj, do_unlink=True)")
        a("")

        # Import animation FBX
        a(f"bpy.ops.import_scene.fbx(filepath=r'{anim}', use_anim=True)")
        a("arm = next((o for o in bpy.context.scene.objects if o.type=='ARMATURE'), None)")
        a("if arm and arm.animation_data:")
        a("    bpy.context.scene.frame_set(1)")
        a("    bpy.context.view_layer.update()")
        a("")

        # Hide Beta_Joints, keep Beta_Surface for rendering
        a("for m in bpy.context.scene.objects:")
        a("    if m.type=='MESH' and m.name=='Beta_Joints':")
        a("        m.hide_render=True; m.hide_viewport=True")
        a("")

        # Collect character AABB (Beta_Surface + armature)
        a("c_mn,c_mx=get_aabb(arm)")
        a("for m in bpy.context.scene.objects:")
        a("    if m.type=='MESH' and m.parent and m.parent.type=='ARMATURE':")
        a("        mn,mx=get_aabb(m)")
        a("        for ax in range(3):")
        a("            if mn[ax]<c_mn[ax]: c_mn[ax]=mn[ax]")
        a("            if mx[ax]>c_mx[ax]: c_mx[ax]=mx[ax]")
        a("ch=c_mx.z-c_mn.z")
        a(f"sys.stderr.write(f'  Char{ci+1}: z=[{{c_mn.z:.2f}},{{c_mx.z:.2f}}] h={{ch:.2f}}\\\\n')")
        a("")

        # Scale furniture
        if target and scl != 1.0:
            a(f"# Scale target furniture {scl}x")
            a("for obj in bpy.context.scene.objects:")
            a(f"    if obj.type=='MESH' and '{target.lower()}' in obj.name.lower():")
            a(f"        obj.scale=({scl},{scl},{scl})")
            a("bpy.context.view_layer.update()")
            a("")

        # Place character
        if target:
            a(f"# Place character on {target}")
            a("furn=None")
            a(f"for obj in bpy.context.scene.objects:")
            a(f"    if obj.type=='MESH' and '{target.lower()}' in obj.name.lower():")
            a("        furn=obj; break")
            a("if furn:")
            a("    f_mn,f_mx=get_aabb(furn)")
            a("    top=f_mx.z")
            a("    sit=c_mn.z+ch*0.40")
            a(f"    dz=top+{clr}-sit")
            a("    cy=(f_mn.y+f_mx.y)/2; ccy=(c_mn.y+c_mx.y)/2; dy=cy-ccy")
            a(f"    sys.stderr.write(f'  Place on {{furn.name}}: dz={{dz:.3f}} dy={{dy:.3f}}\\\\n')")
            a("    arm.location.z+=dz; arm.location.y+=dy")
            a("    bpy.context.view_layer.update()")
            a("")

    # ═══ HDRI ═══
    if hdri:
        a("# ── HDRI ──")
        a("world=bpy.context.scene.world or bpy.data.worlds.new('World')")
        a("bpy.context.scene.world=world")
        a("world.use_nodes=True")
        a("bg=world.node_tree.nodes.get('Background')")
        a("if bg:")
        a("    env=world.node_tree.nodes.new(type='ShaderNodeTexEnvironment')")
        hdri_path = DEFAULTS["hdri_dir"] + "\\\\" + hdri + ".hdr"
        a(f"    env.image=bpy.data.images.load(r'{hdri_path}')")
        a("    world.node_tree.links.new(env.outputs[0],bg.inputs[0])")
        a("    bg.inputs[1].default_value=1.0")
        a("")

    # ═══ Camera + Render ═══
    a("# ── Camera + Render ──")
    a("cam=next((o for o in bpy.context.scene.objects if o.type=='CAMERA'),None)")
    a("if not cam:")
    a("    cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'))")
    a("    bpy.context.scene.collection.objects.link(cam)")
    a("bpy.context.scene.camera=cam")
    a("mn,mx=scene_aabb()")
    a("ctr=(mn+mx)/2")
    a("")

    a(f"scene=bpy.context.scene")
    a(f"scene.render.engine='CYCLES'")
    a(f"scene.cycles.device='GPU'")
    a(f"scene.render.resolution_x={rx}")
    a(f"scene.render.resolution_y={ry}")
    a(f"scene.cycles.samples={samples}")
    a("")

    for shot in camera_shots:
        params = CAMERA_PRESETS.get(shot, CAMERA_PRESETS["medium"])
        ox, oy, oz = params
        a(f"cam.location=ctr+mathutils.Vector(({ox},{oy},{oz}))")
        a("look_at(cam,ctr)")
        a(f"scene.render.filepath=r'{output_dir}\\\\scene_{shot}.png'")
        a("bpy.ops.render.render(write_still=True)")
        a(f"sys.stderr.write(f'[OK] {shot}\\\\n')")
        a("")

    a("print('DONE')")

    return "\n".join(L)


# ── 便捷函数 ──────────────────────────────────────────────────

def living_room(
    animation: str = r"D:\BlenderAgent\animations\motions\sitting_while_laughing_inplace_withskin.fbx",
    position: str = "sofa",
    hdri: str = "kloppenheim_06_4k",
    sofa_scale: float = 1.34,
) -> str:
    """快速生成客厅场景"""
    return render_scene(
        characters=[{"animation": animation, "position": position}],
        hdri=hdri,
        sofa_scale=sofa_scale,
    )


def standing_scene(
    animation: str = r"D:\BlenderAgent\animations\motions\idle_inplace_withskin.fbx",
    hdri: str = "studio_small_03_4k",
) -> str:
    """快速生成站姿场景（不放在家具上）"""
    return render_scene(
        characters=[{"animation": animation}],
        hdri=hdri,
    )
