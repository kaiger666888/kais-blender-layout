# kais-blender-layout — Blender 场景布局引擎

> 一句话生成 Blender 场景参考图。角色 + 家具 + HDRI + 多机位渲染，全自动化。
> Linux → HTTP → Windows Blender 5.1，headless 无 GUI。

## 触发词
`blender-layout`, `场景布局`, `布景`, `layout`, `场景渲染`, `3D 布景`

## 前置依赖
- Windows 端运行 Blender Agent Server（`http://<IP>:8080`）
- 基础场景文件：`D:\BlenderAgent\cache\full_scene.blend`
- Poly Haven 资产已下载（模型 + HDRI）

## 快速使用

```python
from blender_layout import render_scene

script = render_scene(
    characters=[{
        "animation": r"D:\BlenderAgent\animations\motions\sitting_while_laughing_inplace_withskin.fbx",
        "position": "sofa",       # 家具关键词匹配
        "clearance": 0.05,
        "scale": 1.34,            # 家具缩放（修正比例）
    }],
    hdri="kloppenheim_06_4k",
    camera_shots=["wide", "medium", "closeup"],
    sofa_scale=1.34,              # 沙发统一缩放
)
# script → POST /run/script → Blender 执行
```

## 核心能力

### 1. 角色放置（经过实战验证）
- 导入 Mixamo 动画 FBX（含角色 mesh + bake 姿态）
- 删除旧 `Human` mesh（场景残留，不绑定 armature）
- 隐藏 `Beta_Joints`（骨骼可视化），保留 `Beta_Surface`（角色 mesh）
- clearance 机制：坐姿区域 z = 家具顶部 z + clearance

### 2. 家具比例修正
- Poly Haven `sofa_02` 原始太小（0.71m），Mixamo 角色 2m
- 自动缩放沙发到合理比例（默认 1.34x）

### 3. 电影级相机
- 5 种预设镜头：XWS / WS / MS / CU / ECU
- look-at 自动对准场景中心
- Cycles GPU 渲染，128 samples

### 4. HDRI 环境光
- 自动加载 Poly Haven HDRI（路径：`D:\BlenderAgent\assets\polyhaven\hdris\`）

## 踩坑记录（2026-04-18 实战）

| 问题 | 原因 | 解决 |
|------|------|------|
| 角色永远是 T-pose | 渲染的是 `Human` mesh（不绑定 armature）| 删除 Human，保留 Beta_Surface |
| 白色人体模型 | Beta_Surface 被隐藏 | 只隐藏 Beta_Joints |
| 沙发垫悬浮 | 座垫从 Base 里拆出来 | 不拆分，保持原始一体 |
| 比例不对 | 沙发 0.71m vs 角色 2m | 缩放沙发 1.34x |
| AABB 不更新 | 位移后未刷新 | `bpy.context.view_layer.update()` |
| Action 无 fcurves | Blender 5.1 Action Layers 新系统 | 不需要读 fcurves，frame_set 自动应用 |
| 骨骼位置不变 | `matrix_local` 返回 rest pose | 动画通过 depsgraph 应用，渲染正确 |
