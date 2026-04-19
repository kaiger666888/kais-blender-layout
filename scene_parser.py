"""scene_parser.py — 自然语言场景描述解析器

将中文/英文自然语言场景描述转换为结构化的 Blender 场景参数。
纯规则+模板匹配，不调用 LLM API。
"""

import json
import os
import re
import urllib.request
from typing import Dict, List, Optional

# ── 模板目录 ──────────────────────────────────────────────────

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

# ── 关键词映射表 ──────────────────────────────────────────────

# 场景模板关键词 → 模板名
TEMPLATE_KEYWORDS = {
    "coffee_shop": ["咖啡厅", "咖啡", "cafe", "coffee", "茶馆", "下午茶"],
    "office":      ["办公室", "办公", "office", "公司", "写字楼", "工位"],
    "living_room": ["客厅", "起居室", "living room", "家里", "温馨客厅"],
    "bedroom":     ["卧室", "bedroom", "房间", "睡觉"],
    "kitchen":     ["厨房", "kitchen", "做饭", "烹饪"],
    "gym":         ["健身房", "gym", "运动", "锻炼"],
    "lab":         ["实验室", "lab", "laboratory", "科研", "科学"],
    "classroom":   ["教室", "classroom", "课堂", "上课"],
    "bar":         ["酒吧", "bar", "夜店", "pub"],
    "restaurant":  ["餐厅", "restaurant", "饭店", "吃饭"],
    "park":        ["公园", "park", "花园", "garden"],
    "street":      ["街道", "street", "马路", "路边"],
    "hospital":    ["医院", "hospital", "诊所"],
    "library":     ["图书馆", "library", "阅览室"],
}

# 动画关键词 → 动作类别
ANIMATION_KEYWORDS = {
    "sitting":  ["坐", "聊", "喝", "休息", "sit", "chat", "drink", "tea"],
    "standing": ["站", "走", "stand", "walk", "跑步", "run"],
    "fighting": ["打", "fight", "战斗", "拳击", "格斗"],
    "laughing": ["笑", "开心", "laugh", "happy", "愉快"],
    "talking":  ["说话", "讨论", "talk", "discuss", "交谈"],
    "working":  ["工作", "work", "打字", "typing", "电脑"],
    "reading":  ["读书", "看书", "read", "阅读"],
    "dancing":  ["跳舞", "dance", "dancing", "舞蹈"],
    "walking":  ["走路", "散步", "walk", "stroll"],
    "idle":     ["发呆", "等待", "wait", "idle"],
}

# 动作类别 → 默认动画文件名（兜底）
DEFAULT_ANIMATIONS = {
    "sitting":  "sitting_while_laughing_inplace_withskin.fbx",
    "standing": "idle_inplace_withskin.fbx",
    "fighting": "boxing_inplace_withskin.fbx",
    "laughing": "sitting_while_laughing_inplace_withskin.fbx",
    "talking":  "sitting_while_laughing_inplace_withskin.fbx",
    "working":  "idle_inplace_withskin.fbx",
    "reading":  "sitting_while_laughing_inplace_withskin.fbx",
    "dancing":  "dancing_inplace_withskin.fbx",
    "walking":  "idle_inplace_withskin.fbx",
    "idle":     "idle_inplace_withskin.fbx",
}

# 动作类别 → 默认放置位置
DEFAULT_POSITIONS = {
    "sitting":  "sofa",
    "standing": "",
    "fighting": "",
    "laughing": "sofa",
    "talking":  "sofa",
    "working":  "",
    "reading":  "sofa",
    "dancing":  "",
    "walking":  "",
    "idle":     "",
}

# 灯光/氛围关键词
MOOD_KEYWORDS = {
    "warm":     ["温馨", "暖", "warm", "cozy", "舒适", "柔和"],
    "dramatic": ["戏剧", "紧张", "dramatic", "阴暗", "悬疑"],
    "studio":   ["影棚", "studio", "拍摄", "摄影"],
    "outdoor":  ["户外", "outdoor", "室外", "阳光"],
    "cool":     ["冷", "cool", "冷色调", "科技", "科幻"],
    "bright":   ["明亮", "bright", "白天"],
    "dark":     ["黑暗", "dark", "夜晚", "night"],
    "romantic": ["浪漫", "romantic", "烛光"],
}

# 氛围 → HDRI 推荐
MOOD_HDRI = {
    "warm":     "kloppenheim_06_4k",
    "dramatic": "studio_small_03_4k",
    "studio":   "studio_small_03_4k",
    "outdoor":  "puresky_4k",
    "cool":     "industrial_sunset_01_puresky_4k",
    "bright":   "puresky_4k",
    "dark":     "studio_small_03_4k",
    "romantic": "kloppenheim_06_4k",
}

# 中文数字 → 阿拉伯数字
CN_NUMS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


# ── 核心解析函数 ──────────────────────────────────────────────

def parse_scene_request(user_input: str) -> dict:
    """将自然语言场景描述解析为结构化参数。

    输入示例:
        - "两个朋友在咖啡厅聊天"
        - "一个人在办公室工作，暖色调"
        - "科幻实验室，科学家和机器人"
        - "温馨客厅，一家人看电视"

    返回:
        {
            "template": "coffee_shop",
            "characters": [...],
            "mood": "warm",
            "lighting": {"scheme": "warm", "hdri": "kloppenheim_06_4k"},
            "camera_shots": ["wide", "medium", "closeup"],
            "additional_props": [...]
        }
    """
    text = user_input.lower().strip()

    # 1. 匹配场景模板
    template = _match_template(text)

    # 2. 推断角色数量
    char_count = _extract_character_count(text)

    # 3. 匹配动画/动作
    actions = _match_actions(text)

    # 4. 匹配氛围/灯光
    mood = _match_mood(text)

    # 5. 加载模板获取默认值
    tpl_data = _load_template_data(template)

    # 6. 构建角色列表
    characters = _build_characters(char_count, actions, tpl_data)

    # 7. 构建灯光（模板优先，mood 作为补充）
    lighting = dict(tpl_data.get("lighting", {}))
    if mood:
        if "scheme" not in lighting:
            lighting["scheme"] = mood
        if mood in MOOD_HDRI and "hdri" not in lighting:
            lighting["hdri"] = MOOD_HDRI[mood]

    # 8. 收集道具
    additional_props = []
    for item in tpl_data.get("decorations", []):
        additional_props.append(item["asset"])
    for item in tpl_data.get("furniture", []):
        if item.get("asset") and item["asset"] not in additional_props:
            additional_props.append(item["asset"])

    # 9. 镜头默认
    camera_shots = tpl_data.get("camera_defaults", ["wide", "medium", "closeup"])

    return {
        "template": template,
        "characters": characters,
        "mood": mood,
        "lighting": lighting,
        "camera_shots": camera_shots,
        "additional_props": additional_props,
    }


def match_animation(hint: str, available_animations: list) -> str:
    """根据关键词从可用动画中匹配最合适的。

    Args:
        hint: 动作提示，如 "sitting_laughing" 或 "standing"
        available_animations: 可用动画文件名列表

    Returns:
        匹配的动画文件名，兜底返回 DEFAULT_ANIMATIONS 中的默认值
    """
    if not available_animations:
        action = hint.split("_")[0] if "_" in hint else hint
        return DEFAULT_ANIMATIONS.get(action, DEFAULT_ANIMATIONS["idle"])

    parts = [p for p in hint.split("_") if p]
    if not parts:
        return available_animations[0]

    # 精确匹配：所有部分都出现在文件名中
    for anim in available_animations:
        lower = anim.lower()
        if all(p in lower for p in parts):
            return anim

    # 部分匹配：匹配第一个关键词
    for anim in available_animations:
        if parts[0] in anim.lower():
            return anim

    # 任意部分匹配
    for part in parts:
        for anim in available_animations:
            if part in anim.lower():
                return anim

    action = parts[0]
    return DEFAULT_ANIMATIONS.get(action, available_animations[0])


def fetch_available_animations(server_url: str = "http://192.168.71.38:8080") -> List[str]:
    """从 Windows Blender Agent 获取可用动画列表。"""
    url = server_url.rstrip("/") + "/scene-assets?category=animation"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return [a["name"] for a in data.get("assets", [])]
    except Exception:
        return []


def get_available_templates() -> List[str]:
    """扫描 templates/ 目录获取可用模板列表。"""
    templates = []
    if os.path.isdir(TEMPLATES_DIR):
        for f in os.listdir(TEMPLATES_DIR):
            if f.endswith(".json"):
                templates.append(f[:-5])
    return templates


# ── 内部辅助函数 ──────────────────────────────────────────────

def _match_template(text: str) -> str:
    """根据关键词匹配场景模板，返回匹配度最高的模板名。"""
    best = ""
    best_score = 0
    for tpl_name, keywords in TEMPLATE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best = tpl_name
    return best


def _extract_character_count(text: str) -> int:
    """从文本中提取角色数量。"""
    # 匹配 "X个..." 模式（人/朋友/角色/科学家/学生等）
    patterns = [
        r'(\d+)\s*(?:个|位)?(?:人|朋友|角色|科学家|学生|老师|角色)',
        r'(一|二|两|三|四|五|六|七|八|九|十)\s*(?:个|位)?(?:人|朋友|角色|科学家|学生|老师)',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            num_str = m.group(1)
            if num_str.isdigit():
                return int(num_str)
            return CN_NUMS.get(num_str, 1)

    # 特殊关键词推断
    if any(w in text for w in ["朋友", "两人", "两个人", "一对", "双人", "couple"]):
        return 2
    if any(w in text for w in ["一家人", "大家", "一群"]):
        return 3
    if any(w in text for w in ["一个人", "一人", "独自", "孤独"]):
        return 1

    # 默认：提到了具体动作则推测1人
    if any(kw in text for kw in ["坐", "站", "走", "打", "笑", "聊", "work", "sit", "stand"]):
        return 1
    return 0


def _match_actions(text: str) -> List[str]:
    """从文本中匹配动作关键词，返回按匹配度排序的动作列表。"""
    scored = []
    for action, keywords in ANIMATION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((action, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [a for a, _ in scored]


def _match_mood(text: str) -> Optional[str]:
    """从文本中匹配氛围/灯光关键词。"""
    best = None
    best_score = 0
    for mood, keywords in MOOD_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best = mood
    return best


def _load_template_data(template_name: str) -> dict:
    """加载模板 JSON，不存在则返回空 dict。"""
    if not template_name:
        return {}
    path = os.path.join(TEMPLATES_DIR, template_name + ".json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _build_characters(count: int, actions: List[str], tpl_data: dict) -> List[dict]:
    """构建角色参数列表。"""
    if count <= 0:
        return []

    characters = []
    for i in range(count):
        action = actions[i % len(actions)] if actions else "idle"
        # 没有具体动作且有家具时默认坐姿
        if not actions and tpl_data.get("furniture"):
            action = "sitting"

        position = DEFAULT_POSITIONS.get(action, "")
        # 多动作时组合 hint
        if len(actions) > 1:
            hint = "_".join(actions[:2]) if i == 0 else actions[min(i, len(actions) - 1)]
        else:
            hint = action

        characters.append({
            "animation_hint": hint,
            "position": position,
        })

    return characters


# ── 简单测试 ──────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("两个朋友在咖啡厅聊天", {"template": "coffee_shop", "characters": 2}),
        ("一个人在办公室工作", {"template": "office", "characters": 1}),
        ("温馨客厅", {"template": "living_room", "mood": "warm"}),
        ("三个科学家在实验室工作，冷色调", {"template": "lab", "characters": 3, "mood": "cool"}),
        ("A couple dancing in a bar", {"template": "bar", "characters": 2}),
    ]

    print("=== Scene Parser Tests ===\n")
    for text, expected in tests:
        result = parse_scene_request(text)
        print(f"Input:  {text}")
        print(f"Output: {json.dumps(result, ensure_ascii=False, indent=2)}")

        ok = True
        for k, v in expected.items():
            if k == "characters":
                if len(result.get("characters", [])) != v:
                    ok = False
            elif result.get(k) != v:
                ok = False
        print(f"Check:  {'PASS' if ok else 'FAIL'}")
        print()
