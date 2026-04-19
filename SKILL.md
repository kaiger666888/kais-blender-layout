---
name: kais-blender-layout
version: 0.3.0
description: "Blender 场景全流程引擎。AI 场景规划（自然语言→蓝图）+ 场景布局渲染（蓝图→图片）。角色+家具+HDRI+多机位，全自动化。触发词：blender-layout, 场景布局, 布景, layout, 3D 布景, 场景规划, scene planning, scene composition, 分镜转场景, 场景蓝图, 场景搭建"
---

# kais-blender-layout — Blender 场景全流程引擎

> 一句话生成 Blender 场景参考图。
> 自然语言描述 → 场景蓝图 → Blender 渲染，全自动化。
> Linux → HTTP → Windows Blender 5.1，headless 无 GUI。

## 前置依赖

- Windows 端运行 Blender Agent Server（`http://<IP>:8080`，由 kais-blender-engine 提供）
- 基础场景文件：`D:\BlenderAgent\cache\full_scene.blend`
- Poly Haven 资产已下载（模型 + HDRI）

---

## 全流程概览

```
阶段一：场景理解     阶段二：空间推理     阶段三：布局求解     阶段四：渲染执行
────────────────────────────────────────────────────────────────────────────────
自然语言描述  ──→  关系图(JSON)  ──→  场景蓝图(JSON)  ──→  Blender 渲染图片
分镜脚本                                              (调用 engine server)
参考图
```

- **阶段一~三**（规划层）：纯推理，不接触 Blender
- **阶段四**（执行层）：生成 Blender Python 脚本，通过 HTTP 发送到 Windows 端执行

---

## 阶段一：场景理解（Scene Understanding）

将自然语言描述解析为结构化的场景元素。

**输入方式**：
- 自然语言："一个战士在地牢里面对一条龙，旁边有一个宝箱"
- 分镜脚本：从 kais-movie-agent 的分镜输出
- 参考图：截图/概念图

**输出：场景元素列表**

```json
{
  "elements": [
    {"type": "character", "label": "战士", "role": "protagonist"},
    {"type": "character", "label": "龙", "role": "antagonist"},
    {"type": "prop", "label": "宝箱"},
    {"type": "environment", "label": "地牢"}
  ]
}
```

---

## 阶段二：空间推理（Spatial Reasoning）

基于语义关系推理元素之间的空间布局。

<!-- FREEDOM:low -->
**必须使用以下关系类型构建关系图：**

| 关系类型 | 含义 | 约束 |
|---------|------|------|
| `near` | 靠近 | 距离 < 2m |
| `facing` | 面对 | 朝向对方，距离 1-5m |
| `inside` | 在内部 | 位置在环境边界内 |
| `on_top` | 在上方 | Z 轴偏移 |
| `between` | 在之间 | 位于两元素中间 |
| `opposite` | 对立 | 朝向相反，等距 |
| `behind` | 在后方 | Y 轴偏移 |
| `guarding` | 守卫 | 面向目标，近距离 |
| `hiding` | 躲藏 | 在遮挡物后方 |

**关系图输出格式**：
```json
{
  "relations": [
    {"subject": "战士", "relation": "facing", "object": "龙", "distance": 3},
    {"subject": "宝箱", "relation": "near", "object": "龙", "distance": 1.5},
    {"subject": "战士", "relation": "inside", "object": "地牢"},
    {"subject": "龙", "relation": "guarding", "object": "宝箱"}
  ]
}
```
<!-- /FREEDOM:low -->

---

## 阶段三：布局求解（Layout Solving）

将关系图转换为精确的 3D 坐标。

<!-- FREEDOM:low -->
**约束求解规则：**

1. **锚点确定**：环境元素放在原点，主角作为第一锚点
2. **关系展开**：从锚点开始，按关系图 BFS 展开位置
3. **数值约束**：
   - `near`: d ∈ [0.5, 2.0]
   - `facing`: d ∈ [1.0, 5.0], 朝向计算
   - `opposite`: d = 对称距离, rotation ± 180°
   - `guarding`: d ∈ [0.5, 1.5], 面向目标
   - `between`: midpoint(A, B) + 微小偏移
4. **碰撞检测**：任何两个元素间距 > 0.3m
5. **地面约束**：所有元素 Z = 0（地面平面）
<!-- /FREEDOM:low -->

### 灯光方案模板

| 场景氛围 | 方案 | 说明 |
|---------|------|------|
| 戏剧性 | dramatic | 主光 + 补光 + 轮廓光，高对比 |
| 影棚 | studio | 三点布光，均匀柔和 |
| 暗黑 | dark | 低照度，单一冷色光源 |
| 温馨 | warm | 暖色调，环境光为主 |
| 户外 | outdoor | 太阳光 + 天空光 |
| 夜景 | night | 月光 + 点光源（火把/灯） |

### 相机方案模板

| 镜头类型 | 用途 | 参数 |
|---------|------|------|
| 全景 | 展示环境 | 远距离，广角 |
| 中景 | 角色互动 | 中距离，标准焦距 |
| 近景 | 角色表情 | 近距离，长焦 |
| 俯视 | 战略视角 | 正上方 |
| 仰视 | 威慑感 | 低角度，广角 |

### 场景蓝图完整输出

```json
{
  "scene": {
    "name": "dungeon_encounter",
    "description": "战士在地牢中面对守卫宝箱的巨龙"
  },
  "environment": {"name": "地牢", "style": "dark_fantasy"},
  "characters": [
    {"label": "战士", "model_hint": "warrior_knight", "position": [0, 0, 0], "rotation": [0, 0, 0]},
    {"label": "龙", "model_hint": "dragon_red", "position": [0, 3, 0], "rotation": [0, 180, 0]}
  ],
  "props": [
    {"label": "宝箱", "model_hint": "treasure_chest", "position": [1.5, 2, 0]}
  ],
  "lighting": {"scheme": "dramatic"},
  "camera": {
    "shots": [
      {"name": "establishing", "type": "全景", "position": [0, -6, 3], "look_at": [0, 1.5, 0]},
      {"name": "warrior_resolve", "type": "近景", "position": [-0.5, -1.5, 1]}
    ]
  }
}
```

### 自检清单

生成场景蓝图后，必须检查：

- [ ] **空间合理性**：角色间距是否自然？有没有穿模？
- [ ] **视线逻辑**：角色朝向是否符合叙事逻辑？
- [ ] **灯光一致性**：同一场景内灯光方案是否统一？
- [ ] **相机覆盖**：所有关键元素是否在至少一个镜头中可见？
- [ ] **资产匹配度**：model_hint 是否能在资产库中找到对应模型？

---

## 阶段四：渲染执行（Render Execution）

将场景蓝图转换为 Blender Python 脚本，通过 HTTP 发送到 Windows Blender 执行。

### 快速使用

```python
from blender_layout import render_scene

script = render_scene(
    characters=[{
        "animation": r"D:\BlenderAgent\animations\motions\sitting_while_laughing_inplace_withskin.fbx",
        "position": "sofa",       # 家具关键词匹配
        "clearance": 0.05,
        "scale": 1.34,
    }],
    hdri="kloppenheim_06_4k",
    camera_shots=["wide", "medium", "closeup"],
    sofa_scale=1.34,
)
# script → POST http://<IP>:8080/run/script → Blender 执行
```

### 便捷函数

```python
# 客厅场景（角色坐沙发）
script = living_room(animation="...", hdri="kloppenheim_06_4k")

# 站姿场景
script = standing_scene(animation="...", hdri="studio_small_03_4k")
```

### Geometry Nodes 场景增强（v0.3.0 新增）

通过 `geonodes` 参数程序化增强场景环境，无需手动摆放每个道具。

```python
script = render_scene(
    characters=[{"animation": "..."}],
    hdri="kloppenheim_06_4k",
    geonodes={
        "ground": {"size": 10, "density": 50, "seed": 42},
        "scatter": [
            {"target": "Floor", "collection_name": "Props", "density": 3000},
        ],
        "randomize": [
            {"prefix": "sofa_02", "scale_range": (0.95, 1.05)},
        ],
    },
)
```

**geonodes 配置项：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `ground` | dict | `{size, density, seed}` — 程序化地面（碎石散布） |
| `scatter` | list | `{target, collection_name/instance_object, density, seed, scale_min, scale_max, rotate_z, normal_influence}` — 面散布 |
| `instances` | list | `{parent, objects, density, seed, scale_range}` — 多物体随机实例化 |
| `randomize` | list | `{prefix, scale_range, rotation_range, position_offset, seed}` — 随机变换已有物体 |

### 角色放置（经过实战验证）

- 导入 Mixamo 动画 FBX（含角色 mesh + bake 姿态）
- 删除旧 `Human` mesh（场景残留，不绑定 armature）
- 隐藏 `Beta_Joints`（骨骼可视化），保留 `Beta_Surface`（角色 mesh）
- clearance 机制：坐姿区域 z = 家具顶部 z + clearance

### 家具比例修正

- Poly Haven `sofa_02` 原始太小（0.71m），Mixamo 角色 2m
- 自动缩放沙发到合理比例（默认 1.34x）

### 电影级相机

- 5 种预设镜头：XWS / WS / MS / CU / ECU
- look-at 自动对准场景中心
- Cycles GPU 渲染，128 samples

### HDRI 环境光

- 自动加载 Poly Haven HDRI（路径：`D:\BlenderAgent\assets\polyhaven\hdris\`）

---

## 踩坑记录（2026-04-18 实战）

| 问题 | 原因 | 解决 |
|------|------|------|
| 角色永远是 T-pose | 渲染的是 `Human` mesh（不绑定 armature）| 删除 Human，保留 Beta_Surface |
| 白色人体模型 | Beta_Surface 被隐藏 | 只隐藏 Beta_Joints |
| 沙发垫悬浮 | 座垫从 Base 里拆出来 | 不拆分，保持原始一体 |
| 比例不对 | 沙发 0.71m vs 角色 2m | 缩放沙发 1.34x |
| AABB 不更新 | 位移后未刷新 | `bpy.context.view_layer.update()` |
| Action 无 fcurves | Blender 5.1 Action Layers 新系统 | 不需要读 fcurves，frame_set 自动应用 |

---

## 与其他 Skill 的协作

```
kais-movie-agent (分镜脚本)
       ↓
kais-blender-layout (本skill) — 场景蓝图 + 渲染执行
       ↓
kais-blender-engine — 底层 API 服务（动画渲染/姿态渲染）
       ↓
kais-camera (视频生成)
```

**分工说明：**
- **layout（本skill）**：场景规划 + 场景布局渲染（多角色+家具+HDRI+多机位）
- **engine**：底层 API 服务，单角色动画/姿态渲染，资产管理
- ~~**scenecraft**~~：已合并入本 skill（v0.2.0），不再独立维护

## 注意事项

- 场景蓝图是规划层，渲染是执行层，可以单独使用（直接调 `render_scene()` 跳过规划）
- 资产匹配使用 `model_hint` 软匹配，不强依赖具体文件名
- 布局数值可后续微调，重点是空间关系正确
- 同一角色的跨场景位置需要保持连续性
