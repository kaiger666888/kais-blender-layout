---
name: kais-blender-layout
version: 0.1.0
description: "AI驱动的Blender场景智能搭建与角色动作编排引擎。基于SceneCraft思路，通过LLM生成Blender Python脚本，实现Mixamo资产自动导入、场景布局、动画编排和headless渲染。触发词：blender场景搭建, blender layout, 3D场景生成, 场景编排, blender自动化, Mixamo场景, blender脚本, scene builder, character posing, 动作编排, blender headless, 3D管线"
---

# kais-blender-layout

AI 驱动的 Blender 场景智能搭建与角色动作编排引擎。

## 核心思路

```
场景描述(JSON/YAML) → LLM生成Blender Python脚本 → headless执行 → 渲染输出
```

受 SceneCraft（arxiv 2403.01248）启发，简化为实用级：不做双循环视觉反馈（太慢），用结构化约束代替。

## 架构

```
┌─────────────────────────────────────────────┐
│                 输入层                        │
│  场景描述JSON / 分镜脚本 / 自然语言            │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│              资产管理层                       │
│  mixamo_index.sh  扫描FBX元数据               │
│  asset_library.json  模型/动作索引             │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│              布局引擎                         │
│  layout_engine.py  约束求解 + 场景摆放         │
│  - 角色位置/朝向                              │
│  - 道具摆放                                   │
│  - 灯光/相机设置                              │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│              动画编排层                       │
│  animation_timeline.py  NLA时间轴管理          │
│  - Mixamo动画绑定/切换                         │
│  - 动画过渡/混合                               │
│  - 多角色时间线同步                            │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│              渲染管线                         │
│  render_pipeline.py  headless批量渲染          │
│  - 单帧/序列/视频输出                          │
│  - 多机位自动切换                              │
└─────────────────────────────────────────────┘
```

## 前置依赖

- **Blender 3.6+**（推荐 4.x）
- **Python 3.10+**
- Mixamo FBX 素材（本地目录）

检查 Blender 是否可用：
```bash
blender --version
blender --background --python-expr "import bpy; print(bpy.app.version)"
```

## 工作流程

### Step 1: 资产索引

扫描 Mixamo 素材目录，建立索引：

```bash
# 扫描模型和动作
python3 scripts/mixamo_index.py scan --dir /path/to/mixamo/assets --output asset_library.json
```

索引输出格式（asset_library.json）：
```json
{
  "models": [
    {
      "name": "warrior",
      "file": "models/warrior.fbx",
      "type": "character",
      "skeleton": "mixamo"
    }
  ],
  "animations": [
    {
      "name": "walk_forward",
      "file": "animations/walk_forward.fbx",
      "type": "locomotion",
      "frames": 60,
      "fps": 24
    }
  ],
  "environments": [
    {
      "name": "dungeon",
      "file": "environments/dungeon.fbx"
    }
  ]
}
```

### Step 2: 场景定义

用结构化 JSON 定义场景（也支持从自然语言转换）：

```json
{
  "scene": {
    "name": "dungeon_encounter",
    "environment": "dungeon",
    "lighting": {
      "type": "dramatic",
      "key_light": {"position": [5, 8, 3], "color": "warm"},
      "fill_light": {"intensity": 0.3}
    },
    "camera": {
      "position": [0, -5, 2],
      "look_at": "warrior"
    }
  },
  "characters": [
    {
      "model": "warrior",
      "position": [0, 0, 0],
      "rotation": [0, 0, 0],
      "animation": "idle",
      "animation_start": 0
    },
    {
      "model": "dragon",
      "position": [3, 2, 0],
      "rotation": [0, 180, 0],
      "animation": "fly_idle",
      "animation_start": 0
    }
  ],
  "props": [
    {"model": "chest", "position": [2, 1, 0]},
    {"model": "sword", "position": [0.5, 0, 0.5]}
  ],
  "timeline": [
    {"frame": 0, "action": "warrior.idle"},
    {"frame": 60, "action": "warrior.walk_to", "target": [2, 1, 0]},
    {"frame": 120, "action": "warrior.pick_up", "prop": "sword"},
    {"frame": 150, "action": "camera.cut", "angle": "closeup_warrior"}
  ]
}
```

### Step 3: 生成 Blender 脚本

```bash
# 从场景定义生成Python脚本
python3 scripts/layout_engine.py generate --scene scene.json --assets asset_library.json --output scene_setup.py
```

生成的脚本是纯 Blender Python API 调用，可直接执行。

### Step 4: 执行与渲染

```bash
# 方式A：GUI模式（可交互查看）
blender scene_setup.py

# 方式B：Headless批量渲染
blender --background --python scripts/render_pipeline.py \
  -- --scene scene.json \
  --assets asset_library.json \
  --output ./renders/ \
  --format PNG \
  --resolution 1920x1080 \
  --frames 0:180
```

渲染选项：
- `--format PNG|MP4|FFMPEG` — 输出格式
- `--resolution WxH` — 分辨率
- `--frames START:END` — 帧范围
- `--camera all|cam_01` — 相机选择

## 核心脚本说明

| 脚本 | 功能 |
|------|------|
| `scripts/mixamo_index.py` | 扫描FBX文件，提取模型/动作元数据，建立资产索引 |
| `scripts/layout_engine.py` | 根据场景JSON生成Blender Python脚本（导入资产、摆放位置、设置灯光相机） |
| `scripts/layout_engine.py` | NLA时间轴管理已集成：Mixamo动画绑定、切换、过渡、多角色同步 |
| `scripts/render_pipeline.py` | Headless渲染管线：批量出图/出视频、多机位切换 |

## Mixamo 动画处理

### 动画绑定

Mixamo FBX 动画绑定到角色的标准流程：
1. 导入角色模型（带骨架）
2. 导入动画 FBX
3. 提取动画 Action
4. 绑定到角色 Armature
5. 通过 NLA Editor 管理多动画

### NLA 时间轴编排

```python
# 概念示例（实际由 animation_timeline.py 生成）
import bpy

obj = bpy.data.objects["warrior"]
anim_data = obj.animation_data

# 创建NLA轨道
track = anim_data.nla_tracks.new()
# 添加动画片段
track.strips.new("walk", start_frame=0, action=walk_action)
track.strips.new("idle", start_frame=60, action=idle_action)
# 设置过渡
track.strips[1].blend_in = 10  # 10帧过渡
```

### 动画混合

通过 NLA Strip 的 blend mode 实现动画混合：
- `REPLACE` — 完全替换
- `COMBINE` — 叠加
- `ADD` — 相加

## 约束布局规则

布局引擎使用以下约束求解策略：

1. **地面约束** — 所有角色 Z=0（地面平面）
2. **间距约束** — 角色间最小距离 0.5m
3. **朝向约束** — 角色默认面向场景中心或指定目标
4. **相机约束** — 确保所有角色在相机 FOV 内
5. **层级约束** — 道具在地面上方，不穿透

## 集成到视频管线

### 与 kais-movie-agent 对接

在视频管线的"场景生成"环节调用：

```bash
# 1. 从分镜脚本提取场景信息
python3 scripts/layout_engine.py extract --storyboard storyboard.md --output scenes/

# 2. 批量生成所有场景
for scene in scenes/*.json; do
  python3 scripts/layout_engine.py generate --scene "$scene" --assets asset_library.json --output "scripts/${scene##*/}.py"
done

# 3. 批量渲染
blender --background --python scripts/render_pipeline.py -- --batch-dir scenes/ --assets asset_library.json --output ./renders/
```

### 与 kais-camera 对接

渲染输出可作为 AI 视频生成的参考图或直接用于合成。

## 错误处理

- FBX 导入失败 → 记录错误，跳过该资产，继续处理其他
- 骨架不匹配 → 检测 Mixamo 标准骨架，自动重定向
- 渲染超时 → 分段渲染，支持断点续传
- 内存不足 → 降低分辨率，减少同时加载的资产

## 配置

在项目根目录创建 `blender_config.json`：
```json
{
  "blender_path": "/usr/bin/blender",
  "assets_dir": "/path/to/mixamo/assets",
  "render_output": "./renders",
  "default_resolution": [1920, 1080],
  "default_fps": 24,
  "render_engine": "CYCLES"
}
```

## 注意事项

- Blender headless 渲染需要 GPU 或足够的 CPU 资源
- Mixamo FBX 文件较大，首次加载可能较慢
- 复杂场景（>20个角色）建议分批渲染
- Cycles 渲染质量高但慢，Eevee 快但效果一般，根据需求选择
