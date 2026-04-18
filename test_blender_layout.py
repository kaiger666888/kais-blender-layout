"""测试 blender_layout 模块"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender_layout import render_scene, living_room, standing_scene

# 测试客厅场景
script = living_room()
print(f"living_room: {len(script)} chars")

# 测试自定义场景
script2 = render_scene(
    characters=[{
        "animation": r"D:\BlenderAgent\animations\motions\sitting_unethusiastic_clap_inplace_withskin.fbx",
        "position": "sofa",
    }],
    hdri="studio_small_03_4k",
    camera_shots=["wide", "closeup"],
)
print(f"custom: {len(script2)} chars")

# 验证关键内容
assert "sofa_scale" in script
assert "Beta_Joints" in script
assert "Beta_Surface" not in script or "Beta_Joints" in script
assert "view_layer.update()" in script
assert "Human" in script  # 删除旧 mesh
assert "kloppenheim" in script
print("All assertions passed!")
