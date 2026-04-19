"""kais-blender-layout — Geometry Nodes 场景增强模块

通过 Python 动态创建 Geometry Nodes 修改器，程序化增强场景：
- Scatter on Surface: 在面上散布道具（草、碎石、装饰）
- Instance Collection: 批量实例化模型集合
- Procedural Ground: 程序化地面细节
- Randomize Transform: 随机变换

所有函数返回 Blender Python 脚本片段，嵌入 render_scene() 主脚本中执行。
"""

from typing import Dict, List, Optional


def scatter_on_surface(
    target: str = "Floor",
    instance_object: str = None,
    collection_name: str = None,
    density: float = 5000,
    seed: int = 42,
    scale_min: float = 0.8,
    scale_max: float = 1.2,
    rotate_z: bool = True,
    normal_influence: float = 0.0,
) -> str:
    """在目标面上散布物体或集合。

    Args:
        target: 目标面名称（如 "Floor", "Wall_Back"）
        instance_object: 要散布的单个物体名称
        collection_name: 要散布的集合名称（与 instance_object 二选一）
        density: 每平方米散布密度
        seed: 随机种子
        scale_min: 最小缩放
        scale_max: 最大缩放
        rotate_z: 是否随机旋转 Z 轴
        normal_influence: 法线方向偏移强度（0=贴面，>0=浮起）

    Returns:
        Blender Python 脚本片段（str）
    """
    L = []
    a = L.append

    a(f"# ── GeoNodes: Scatter on '{target}' ──")
    a(f"_scatter_target = '{target}'")
    a("_scatter_obj = bpy.data.objects.get(_scatter_target)")
    a("if _scatter_obj and _scatter_obj.type == 'MESH':")
    a("    # Create GeoNodes tree")
    a(f"    _ng = bpy.data.node_groups.new('Scatter_{_scatter_target}', 'GeometryNodeTree')")
    a("    _ng.interface.new_socket('Geometry', 'INPUT', 'NodeSocketGeometry')")
    a("    _ng.interface.new_socket('Geometry', 'OUTPUT', 'NodeSocketGeometry')")
    a("")
    a("    # Input")
    a("    _ng_in = _ng.nodes.new('NodeGroupInput')")
    a("    _ng_out = _ng.nodes.new('NodeGroupOutput')")
    a("")
    a("    # Distribute points on faces")
    a("    _dist = _ng.nodes.new('GeometryNodeDistributePointsOnFaces')")
    a(f"    _dist.density = {density}")
    a(f"    _dist.seed = {seed}")
    a("")
    a("    # Random scale")
    a("    _rnd_scale = _ng.nodes.new('FunctionNodeRandomValue')")
    a(f"    _rnd_scale.data_type = 'FLOAT'")
    a(f"    _rnd_scale.inputs[1].default_value = {scale_min}")
    a(f"    _rnd_scale.inputs[2].default_value = {scale_max}")
    a("")
    a("    # Random rotation Z")
    a(f"    _rnd_rot = _ng.nodes.new('FunctionNodeRandomValue')")
    a(f"    _rnd_rot.data_type = 'FLOAT'")
    a(f"    _rnd_rot.inputs[1].default_value = 0")
    a(f"    _rnd_rot.inputs[2].default_value = {3.14159 if rotate_z else 0.0}")
    a("")

    # Instance source: collection or single object
    if collection_name:
        a(f"    # Instance from collection: {collection_name}")
        a(f"    _coll_info = _ng.nodes.new('GeometryNodeCollectionInfo')")
        a(f"    _coll_info.inputs['Collection'].default_value = ''")  # set below")
        a("")
        a("    _inst = _ng.nodes.new('GeometryNodeInstanceOnPoints')")
        a("    _inst.inputs['Pick Instance'].default_value = True")
        a("")
    else:
        a(f"    # Instance single object: {instance_object}")
        a(f"    _obj_info = _ng.nodes.new('GeometryNodeObjectInfo')")
        a(f"    _obj_info.inputs['Object'].default_value = ''")  # set below")
        a("")
        a("    _inst = _ng.nodes.new('GeometryNodeInstanceOnPoints')")
        a("")

    a("    # Set Position")
    a("    _set_pos = _ng.nodes.new('GeometryNodeSetPosition')")
    a(f"    _set_pos.inputs['Offset'].default_value = (0, 0, {normal_influence})")
    a("    _set_pos.inputs['Offset'].data_type = 'FLOAT_VECTOR'")
    a("")

    a("    # Realize instances")
    a("    _realize = _ng.nodes.new('GeometryNodeRealizeInstances')")
    a("")

    # Links
    a("    _ng.links.new(_ng_in.outputs['Geometry'], _dist.inputs['Mesh'])")

    if collection_name:
        a("    _ng.links.new(_dist.outputs['Points'], _inst.inputs['Points'])")
        a("    _ng.links.new(_rnd_scale.outputs[0], _inst.inputs['Scale'])")
        a("    _ng.links.new(_rnd_rot.outputs[0], _inst.inputs['Rotation'])")
        a("    _ng.links.new(_inst.outputs['Instances'], _set_pos.inputs['Instance'])")
        a("    _ng.links.new(_set_pos.outputs['Geometry'], _realize.inputs['Geometry'])")
        a("    _ng.links.new(_realize.outputs['Geometry'], _ng_out.inputs['Geometry'])")
    else:
        a("    _ng.links.new(_dist.outputs['Points'], _inst.inputs['Points'])")
        a("    _ng.links.new(_rnd_scale.outputs[0], _inst.inputs['Scale'])")
        a("    _ng.links.new(_rnd_rot.outputs[0], _inst.inputs['Rotation'])")
        a("    _ng.links.new(_inst.outputs['Instances'], _set_pos.inputs['Instance'])")
        a("    _ng.links.new(_set_pos.outputs['Geometry'], _realize.inputs['Geometry'])")
        a("    _ng.links.new(_realize.outputs['Geometry'], _ng_out.inputs['Geometry'])")
    a("")

    # Apply modifier
    a("    _mod = _scatter_obj.modifiers.new('Scatter_GeoNodes', 'NODES')")
    a("    _mod.node_group = _ng")
    a("    bpy.context.view_layer.update()")

    # Set collection reference after modifier is applied
    if collection_name:
        a(f"    for node in _mod.node_group.nodes:")
        a(f"        if node.type == 'GeometryNodeCollectionInfo':")
        a(f"            for coll in bpy.data.collections:")
        a(f"                if coll.name == '{collection_name}':")
        a(f"                    node.inputs['Collection'].default_value = coll.name")
    else:
        a(f"    for node in _mod.node_group.nodes:")
        a(f"        if node.type == 'GeometryNodeObjectInfo':")
        a(f"            obj_ref = bpy.data.objects.get('{instance_object}')")
        a(f"            if obj_ref:")
        a(f"                node.inputs['Object'].default_value = obj_ref.name")

    a(f"    sys.stderr.write('[geonodes] Scatter applied to {_scatter_target} (density={density}, seed={seed})\\\\n')")
    a("else:")
    a(f"    sys.stderr.write('[geonodes] WARNING: target {{_scatter_target}} not found\\\\n')")
    a("")

    return "\n".join(L)


def instance_on_points(
    parent: str = "Floor",
    objects: List[str] = None,
    density: int = 100,
    seed: int = 42,
    scale_range: tuple = (0.5, 2.0),
    ground_cling: bool = True,
) -> str:
    """在面上实例化多个不同物体（随机选择）。

    Args:
        parent: 父面名称
        objects: 要实例化的物体名称列表
        density: 散布点数
        seed: 随机种子
        scale_range: (min, max) 缩放范围
        ground_cling: 是否贴紧地面

    Returns:
        Blender Python 脚本片段
    """
    L = []
    a = L.append

    a(f"# ── GeoNodes: Instance on Points on '{parent}' ──")
    a(f"_iop_parent = bpy.data.objects.get('{parent}')")
    a("if _iop_parent and _iop_parent.type == 'MESH':")
    a(f"    _ng = bpy.data.node_groups.new('InstanceOnPoints_{parent}', 'GeometryNodeTree')")
    a("    _ng.interface.new_socket('Geometry', 'INPUT', 'NodeSocketGeometry')")
    a("    _ng.interface.new_socket('Geometry', 'OUTPUT', 'NodeSocketGeometry')")
    a("    _ng_in = _ng.nodes.new('NodeGroupInput')")
    a("    _ng_out = _ng.nodes.new('NodeGroupOutput')")
    a("")

    # Distribute points
    a("    _dist = _ng.nodes.new('GeometryNodeDistributePointsOnFaces')")
    a(f"    _dist.density = {density}")
    a(f"    _dist.seed = {seed}")
    a("")

    # Random value for object index
    a("    _rnd_idx = _ng.nodes.new('FunctionNodeRandomValue')")
    a("    _rnd_idx.data_type = 'INT'")
    a(f"    _rnd_idx.inputs[1].default_value = 0")
    a(f"    _rnd_idx.inputs[2].default_value = {len(objects) if objects else 1}")
    a("")

    # Random scale
    a("    _rnd_scl = _ng.nodes.new('FunctionNodeRandomValue')")
    a("    _rnd_scl.data_type = 'FLOAT'")
    a(f"    _rnd_scl.inputs[1].default_value = {scale_range[0]}")
    a(f"    _rnd_scl.inputs[2].default_value = {scale_range[1]}")
    a("")

    # Random rotation
    a("    _rnd_rot = _ng.nodes.new('FunctionNodeRandomValue')")
    a("    _rnd_rot.data_type = 'FLOAT'")
    a("    _rnd_rot.inputs[1].default_value = 0")
    a("    _rnd_rot.inputs[2].default_value = 6.283")
    a("")

    # Instance on Points with Pick Instance
    a("    _inst = _ng.nodes.new('GeometryNodeInstanceOnPoints')")
    a("    _inst.inputs['Pick Instance'].default_value = True")
    a("")

    # Realize
    a("    _realize = _ng.nodes.new('GeometryNodeRealizeInstances')")
    a("")

    # Links
    a("    _ng.links.new(_ng_in.outputs['Geometry'], _dist.inputs['Mesh'])")
    a("    _ng.links.new(_dist.outputs['Points'], _inst.inputs['Points'])")
    a("    _ng.links.new(_rnd_idx.outputs[0], _inst.inputs['Instance Index'])")
    a("    _ng.links.new(_rnd_scl.outputs[0], _inst.inputs['Scale'])")
    a("    _ng.links.new(_rnd_rot.outputs[0], _inst.inputs['Rotation'])")
    a("    _ng.links.new(_inst.outputs['Instances'], _realize.inputs['Geometry'])")
    a("    _ng.links.new(_realize.outputs['Geometry'], _ng_out.inputs['Geometry'])")
    a("")

    # Apply
    a("    _mod = _iop_parent.modifiers.new('InstanceOnPoints', 'NODES')")
    a("    _mod.node_group = _ng")
    a("    bpy.context.view_layer.update()")
    a(f"    sys.stderr.write('[geonodes] InstanceOnPoints on {{parent}} ({density} instances, {len(objects)} object types)\\\\n')")
    a("else:")
    a(f"    sys.stderr.write('[geonodes] WARNING: parent {{'{parent}'}} not found\\\\n')")
    a("")

    return "\n".join(L)


def procedural_ground_detail(
    size: float = 10,
    grass_density: int = 2000,
    rock_density: int = 50,
    seed: int = 42,
) -> str:
    """程序化地面：散布草地和碎石。

    Args:
        size: 地面大小
        grass_density: 草密度
        rock_density: 碎石密度
        seed: 随机种子

    Returns:
        Blender Python 脚本片段
    """
    L = []
    a = L.append

    a("# ── GeoNodes: Procedural Ground Detail ──")
    a(f"_ground_size = {size}")
    a("")

    # Create ground plane
    a("bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=False)")
    a("_ground = bpy.context.active_object")
    a("_ground.name = 'Procedural_Ground'")
    a(f"_ground.scale = ({size}, {size}, 1)")
    a("_ground.location = (0, 0, 0)")
    a("")

    # Ground material
    a("_mat_ground = bpy.data.materials.new('Mat_Ground')")
    a("_mat_ground.use_nodes = True")
    a("_mat_ground.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.25, 0.4, 0.15, 1.0)")
    a("_mat_ground.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95")
    a("_ground.data.materials.append(_mat_ground)")
    a("")

    # Scatter small cubes as rocks (simple approach, no external assets needed)
    a("# Rock scatter")
    a(f"_rock_ng = bpy.data.node_groups.new('RockScatter', 'GeometryNodeTree')")
    a("_rock_ng.interface.new_socket('Geometry', 'INPUT', 'NodeSocketGeometry')")
    a("_rock_ng.interface.new_socket('Geometry', 'OUTPUT', 'NodeSocketGeometry')")
    a("_r_in = _rock_ng.nodes.new('NodeGroupInput')")
    a("_r_out = _rock_ng.nodes.new('NodeGroupOutput')")
    a("_r_dist = _rock_ng.nodes.new('GeometryNodeDistributePointsOnFaces')")
    a(f"_r_dist.density = {rock_density}")
    a(f"_r_dist.seed = {seed}")
    a("_r_cube = _rock_ng.nodes.new('GeometryNodeMeshIcoSphere')")
    a(f"_r_cube.inputs['Radius'].default_value = 0.05")
    a("_r_rnd = _rock_ng.nodes.new('FunctionNodeRandomValue')")
    a("_r_rnd.data_type = 'FLOAT_VECTOR'")
    a("_r_rnd.inputs[2].default_value = (1.5, 1.5, 1.5)")
    a("_r_inst = _rock_ng.nodes.new('GeometryNodeInstanceOnPoints')")
    a("_r_real = _rock_ng.nodes.new('GeometryNodeRealizeInstances')")
    a("_rock_ng.links.new(_r_in.outputs['Geometry'], _r_dist.inputs['Mesh'])")
    a("_rock_ng.links.new(_r_dist.outputs['Points'], _r_inst.inputs['Points'])")
    a("_rock_ng.links.new(_r_rnd.outputs[0], _r_inst.inputs['Scale'])")
    a("_rock_ng.links.new(_r_inst.outputs['Instances'], _r_real.inputs['Geometry'])")
    a("_rock_ng.links.new(_r_real.outputs['Geometry'], _r_out.inputs['Geometry'])")
    a("_rock_mod = _ground.modifiers.new('RockScatter', 'NODES')")
    a("_rock_mod.node_group = _rock_ng")
    a("")

    a("bpy.context.view_layer.update()")
    a(f"sys.stderr.write('[geonodes] Ground detail: {size}m plane, {rock_density} rocks\\\\n')")
    a("")

    return "\n".join(L)


def randomize_existing_objects(
    prefix: str = "",
    scale_range: tuple = (0.9, 1.1),
    rotation_range: tuple = (-15, 15),
    position_offset: float = 0.1,
    seed: int = 42,
) -> str:
    """对已有场景中匹配名称前缀的物体随机变换。

    Args:
        prefix: 物体名称前缀筛选
        scale_range: 缩放随机范围
        rotation_range: Z 轴旋转范围（度）
        position_offset: 位置偏移范围
        seed: 随机种子

    Returns:
        Blender Python 脚本片段
    """
    L = []
    a = L.append

    a(f"# ── GeoNodes: Randomize objects (prefix='{prefix}') ──")
    a(f"import random")
    a(f"random.seed({seed})")
    a(f"_count = 0")
    a(f"for obj in bpy.context.scene.objects:")
    a(f"    if obj.type == 'MESH' and obj.name.startswith('{prefix}'):")
    a(f"        obj.scale = tuple(s * random.uniform({scale_range[0]}, {scale_range[1]}) for s in obj.scale)")
    a(f"        obj.rotation_euler.z += math.radians(random.uniform({rotation_range[0]}, {rotation_range[1]}))")
    a(f"        obj.location.x += random.uniform(-{position_offset}, {position_offset})")
    a(f"        obj.location.y += random.uniform(-{position_offset}, {position_offset})")
    a(f"        _count += 1")
    a(f"bpy.context.view_layer.update()")
    a(f"sys.stderr.write('[geonodes] Randomized {_count} objects (prefix={prefix})\\\\n')")
    a("")

    return "\n".join(L)


# ── 组合：完整场景增强 ──

def scene_enhancement(
    scatter_surfaces: List[Dict] = None,
    instance_groups: List[Dict] = None,
    randomize_prefixes: List[Dict] = None,
    ground_detail: bool = False,
    ground_size: float = 10,
) -> str:
    """生成完整的场景增强脚本片段。

    Args:
        scatter_surfaces: [{target, collection_name, density, seed, ...}]
        instance_groups: [{parent, objects, density, seed, ...}]
        randomize_prefixes: [{prefix, scale_range, rotation_range, ...}]
        ground_detail: 是否添加程序化地面细节
        ground_size: 地面大小

    Returns:
        完整的 Blender Python 脚本片段
    """
    L = []
    a = L.append
    a("import math")

    if ground_detail:
        L.append(procedural_ground_detail(size=ground_size, seed=42))

    if scatter_surfaces:
        for s in scatter_surfaces:
            L.append(scatter_on_surface(**s))

    if instance_groups:
        for g in instance_groups:
            L.append(instance_on_points(**g))

    if randomize_prefixes:
        for r in randomize_prefixes:
            L.append(randomize_existing_objects(**r))

    return "\n".join(L)
