"""layout_solver.py — 道具空间关系推理系统

将自然语言空间关系（靠墙、角落、在...旁边等）转换为精确的 3D 坐标。
支持混合格式：有 position 就用 position，没有就根据 relation 求解。

用法:
    from layout_solver import LayoutSolver
    solver = LayoutSolver(room_width=6, room_depth=5, room_height=3)
    solver.place("sofa", [2, 1, 0.8], "center")
    solver.place("bookshelf", [0.4, 1.8, 0.6], "against_wall", wall="right")
    solver.place("plant", [0.3, 0.3, 0.5], "corner", corner="back_right")
    result = solver.get_all_positions()  # {name: [x, y, z]}
"""

import math

# ── 空间关系定义 ──────────────────────────────────────────────

RELATIONS = {
    "center": "放在房间中央",
    "against_wall": "靠墙放置（需要 wall 参数：front/back/left/right）",
    "near": "靠近目标物体（需要 target + offset）",
    "on_top": "放在目标物体上面（需要 target）",
    "corner": "放在角落（需要 corner 参数：front_left/front_right/back_left/back_right）",
    "facing": "朝向目标物体",
    "between": "在两个物体之间（需要 target_a + target_b）",
    "side": "在目标物体的某一侧（需要 side 参数：left/right）",
}

# ── 默认尺寸表（常见道具的近似包围盒，单位：米）────────────

DEFAULT_SIZES = {
    "sofa": [2.0, 0.9, 0.8],
    "armchair": [0.8, 0.8, 0.9],
    "bookshelf": [1.2, 0.4, 1.8],
    "table": [1.2, 0.8, 0.75],
    "coffee_table": [1.0, 0.6, 0.45],
    "desk": [1.4, 0.7, 0.75],
    "tv": [1.2, 0.1, 0.7],
    "chair": [0.5, 0.5, 0.9],
    "plant": [0.3, 0.3, 0.5],
    "lamp": [0.3, 0.3, 1.5],
    "lantern": [0.25, 0.25, 0.4],
    "camera": [0.15, 0.15, 0.2],
    "rug": [2.0, 1.5, 0.02],
    "shelf": [0.8, 0.3, 1.2],
    "cabinet": [0.6, 0.4, 1.8],
    "side_table": [0.4, 0.4, 0.6],
    "bust": [0.3, 0.3, 0.4],
    "fern": [0.4, 0.4, 0.6],
    "bed": [2.0, 1.5, 0.5],
    "wardrobe": [1.8, 0.6, 2.2],
}

# 碰撞检测最小间距（米）
MIN_CLEARANCE = 0.15


class LayoutSolver:
    """空间关系布局求解器。

    坐标系（Blender 默认）:
        X: 左(-) → 右(+)
        Y: 前(-) → 后(+)
        Z: 下(-) → 上(+)

    房间中心在原点 (0, 0, 0)。
    """

    def __init__(self, room_width, room_depth, room_height):
        self.room_width = room_width
        self.room_depth = room_depth
        self.room_height = room_height
        self.placed = {}  # name -> {"position": [x,y,z], "size": [w,d,h], "relation": str}

    def _get_half_room(self):
        return self.room_width / 2, self.room_depth / 2

    def _wall_margin(self, size):
        """靠墙时留出半个物体宽度+一点间距。"""
        return size[0] / 2 + MIN_CLEARANCE

    def _depth_margin(self, size):
        return size[1] / 2 + MIN_CLEARANCE

    def place(self, name, size=None, relation="center", **kwargs):
        """计算单个物体的位置并记录。

        Args:
            name: 物体名称（唯一标识）
            size: [width, depth, height] 包围盒尺寸，None 则查 DEFAULT_SIZES
            relation: 空间关系类型
            **kwargs: 关系参数（wall, target, corner, side, offset 等）

        Returns:
            [x, y, z] 计算出的位置
        """
        if size is None:
            # 尝试从 type 或 name 推断
            item_type = kwargs.get("type", name.lower())
            size = DEFAULT_SIZES.get(item_type, [0.5, 0.5, 0.5])

        pos = self._compute_position(name, size, relation, **kwargs)
        self.placed[name] = {
            "position": pos,
            "size": list(size),
            "relation": relation,
        }
        return pos

    def _compute_position(self, name, size, relation, **kwargs):
        """根据空间关系计算位置坐标。"""
        hw, hd = self._get_half_room()
        w, d, h = size

        if relation == "center":
            return [0.0, 0.0, h / 2]

        elif relation == "against_wall":
            wall = kwargs.get("wall", "back")
            margin = self._wall_margin(size)
            d_margin = self._depth_margin(size)
            if wall == "back":
                return [0.0, hd - d_margin, h / 2]
            elif wall == "front":
                return [0.0, -(hd - d_margin), h / 2]
            elif wall == "left":
                return [-(hw - margin), 0.0, h / 2]
            elif wall == "right":
                return [hw - margin, 0.0, h / 2]
            else:
                raise ValueError("Unknown wall: " + str(wall) + " (use front/back/left/right)")

        elif relation == "corner":
            corner = kwargs.get("corner", "back_left")
            x_margin = self._wall_margin(size)
            y_margin = self._depth_margin(size)
            corners = {
                "front_left": [-(hw - x_margin), -(hd - y_margin)],
                "front_right": [hw - x_margin, -(hd - y_margin)],
                "back_left": [-(hw - x_margin), hd - y_margin],
                "back_right": [hw - x_margin, hd - y_margin],
            }
            if corner not in corners:
                raise ValueError("Unknown corner: " + str(corner))
            cx, cy = corners[corner]
            return [cx, cy, h / 2]

        elif relation == "near":
            target = kwargs.get("target")
            offset = kwargs.get("offset", [0.5, 0.5, 0])
            if target and target in self.placed:
                tp = self.placed[target]["position"]
                return [tp[0] + offset[0], tp[1] + offset[1], tp[2] + offset[2]]
            else:
                # fallback: center with offset
                return [offset[0], offset[1], h / 2 + offset[2]]

        elif relation == "on_top":
            target = kwargs.get("target")
            if target and target in self.placed:
                tp = self.placed[target]["position"]
                ts = self.placed[target]["size"]
                return [tp[0], tp[1], tp[2] + ts[2] / 2 + h / 2]
            else:
                return [0.0, 0.0, h / 2]

        elif relation == "side":
            target = kwargs.get("target")
            side = kwargs.get("side", "right")
            if target and target in self.placed:
                tp = self.placed[target]["position"]
                ts = self.placed[target]["size"]
                gap = ts[0] / 2 + w / 2 + MIN_CLEARANCE
                if side == "right":
                    return [tp[0] + gap, tp[1], tp[2]]
                elif side == "left":
                    return [tp[0] - gap, tp[1], tp[2]]
                else:
                    raise ValueError("Unknown side: " + str(side) + " (use left/right)")
            else:
                return [0.0, 0.0, h / 2]

        elif relation == "between":
            target_a = kwargs.get("target_a")
            target_b = kwargs.get("target_b")
            perp_offset = kwargs.get("perp_offset", 0)
            if target_a and target_b and target_a in self.placed and target_b in self.placed:
                pa = self.placed[target_a]["position"]
                pb = self.placed[target_b]["position"]
                mx = (pa[0] + pb[0]) / 2
                my = (pa[1] + pb[1]) / 2
                mz = max(pa[2], pb[2])
                # 垂直偏移（沿 AB 连线的法线方向）
                dx = pb[0] - pa[0]
                dy = pb[1] - pa[1]
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0.01:
                    nx, ny = -dy / length, dx / length
                    return [mx + nx * perp_offset, my + ny * perp_offset, mz]
                return [mx, my, mz]
            else:
                return [0.0, 0.0, h / 2]

        elif relation == "facing":
            # facing 不影响位置，只标记朝向（用于后续旋转计算）
            # fallback 到 center
            return [0.0, 0.0, h / 2]

        else:
            raise ValueError("Unknown relation: " + str(relation) + ". Use one of: " + ", ".join(RELATIONS.keys()))

    def check_collision(self, name, position, size):
        """检查是否与已放置物体碰撞（AABB 重叠检测）。

        Returns:
            (collided: bool, colliding_with: list of names)
        """
        colliding = []
        px, py, pz = position
        hw, hd, hh = size[0] / 2, size[1] / 2, size[2] / 2

        for other_name, other in self.placed.items():
            if other_name == name:
                continue
            op = other["position"]
            os = other["size"]
            ohw, ohd, ohh = os[0] / 2, os[1] / 2, os[2] / 2

            # AABB overlap test
            overlap_x = abs(px - op[0]) < hw + ohw - MIN_CLEARANCE
            overlap_y = abs(py - op[1]) < hd + ohd - MIN_CLEARANCE
            overlap_z = abs(pz - op[2]) < hh + ohh - MIN_CLEARANCE

            if overlap_x and overlap_y and overlap_z:
                colliding.append(other_name)

        return len(colliding) > 0, colliding

    def solve_all(self, items):
        """批量求解所有物体位置。

        Args:
            items: 物体列表，每个是 dict:
                - name: 唯一标识（可选，默认用 asset）
                - asset: 资产名称
                - type: 物体类型（可选，用于查默认尺寸）
                - size: [w, d, h]（可选）
                - relation: 空间关系（可选）
                - position: [x, y, z] 硬编码位置（可选，优先使用）
                - 其他关系参数

        Returns:
            dict: {name: {"position": [x,y,z], "size": [w,d,h], ...}}
        """
        result = {}
        for item in items:
            item_name = item.get("name", item.get("asset", "unknown"))
            size = item.get("size", None)
            position = item.get("position", None)
            relation = item.get("relation", None)

            if position is not None:
                # 硬编码位置，直接使用
                if size is None:
                    item_type = item.get("type", item_name.lower())
                    size = DEFAULT_SIZES.get(item_type, [0.5, 0.5, 0.5])
                result[item_name] = {
                    "position": list(position),
                    "size": list(size),
                    "relation": "explicit",
                }
                self.placed[item_name] = result[item_name]
            elif relation is not None:
                # 用空间关系求解
                pos = self.place(
                    item_name,
                    size=size,
                    relation=relation,
                    type=item.get("type", item_name.lower()),
                    **{k: v for k, v in item.items() if k not in ("name", "asset", "type", "size", "position", "relation", "rotation", "scale")},
                )
                result[item_name] = self.placed[item_name]
            else:
                # 没有位置也没有关系，默认 center
                pos = self.place(item_name, size=size, relation="center", type=item.get("type", item_name.lower()))
                result[item_name] = self.placed[item_name]

        return result

    def get_all_positions(self):
        """获取所有已放置物体的位置。"""
        return {name: info["position"] for name, info in self.placed.items()}

    def get_rotation_from_relation(self, name):
        """根据空间关系推断物体的旋转角度（度）。

        against_wall left/right -> 90/-90
        corner 需要特殊处理
        facing -> 面向目标的角度
        """
        info = self.placed.get(name)
        if not info:
            return 0

        rel = info.get("relation", "")

        # 这些关系需要额外的 kwargs，这里返回 0 让模板的 rotation 覆盖
        if rel == "against_wall":
            # 可从 kwargs 推断，但 solve_all 不保存 kwargs
            # 返回 0，由模板 rotation 字段决定
            return 0
        elif rel == "corner":
            return 0
        return 0

    def report(self):
        """生成布局报告字符串。"""
        lines = []
        lines.append("Layout Solver Report")
        lines.append("=" * 50)
        lines.append("Room: " + str(self.room_width) + " x " + str(self.room_depth) + " x " + str(self.room_height) + " m")
        lines.append("Placed objects: " + str(len(self.placed)))
        lines.append("")

        for name, info in self.placed.items():
            pos = info["position"]
            sz = info["size"]
            rel = info.get("relation", "explicit")
            lines.append("  " + name + ":")
            lines.append("    position: [" + ", ".join("{:.2f}".format(v) for v in pos) + "]")
            lines.append("    size:     [" + ", ".join("{:.2f}".format(v) for v in sz) + "]")
            lines.append("    relation: " + rel)

            collided, with_what = self.check_collision(name, pos, sz)
            if collided:
                lines.append("    WARNING: collision with " + ", ".join(with_what))

        return "\n".join(lines)
