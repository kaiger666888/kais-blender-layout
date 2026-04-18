#!/usr/bin/env python3
"""
Blender Headless 渲染管线
支持批量渲染、多机位、断点续传
"""

import argparse
import json
import os
import sys
from pathlib import Path


def generate_render_script(scenes_dir: str, assets_data: dict, output_dir: str, config: dict) -> str:
    """生成批量渲染脚本"""
    
    lines = [
        '"""',
        'Auto-generated render pipeline by kais-blender-layout',
        '"""',
        '',
        'import bpy',
        'import os',
        'import sys',
        '',
        f'OUTPUT_DIR = r"{output_dir}"',
        f'RESOLUTION = {config.get("resolution", [1920, 1080])}',
        f'FPS = {config.get("fps", 24)}',
        f'RENDER_ENGINE = "{config.get("render_engine", "BLENDER_EEVEE_NEXT")}"',
        '',
        'os.makedirs(OUTPUT_DIR, exist_ok=True)',
        '',
        '# 渲染设置',
        'scene = bpy.context.scene',
        'scene.render.engine = RENDER_ENGINE',
        'scene.render.resolution_x = RESOLUTION[0]',
        'scene.render.resolution_y = RESOLUTION[1]',
        'scene.render.fps = FPS',
        'scene.render.image_settings.file_format = "PNG"',
        'scene.render.image_settings.color_mode = "RGBA"',
        '',
    ]
    
    if config.get("render_engine", "") in ["CYCLES", "CYCLES_X"]:
        lines.extend([
            '# Cycles 优化设置',
            'scene.cycles.samples = 64',
            'scene.cycles.use_denoising = True',
            'scene.cycles.device = "GPU" if bpy.context.preferences.addons.get("cycles") else "CPU"',
            '',
        ])
    
    # 扫描场景目录
    scenes_path = Path(scenes_dir)
    scene_files = sorted(scenes_path.glob("*.json"))
    
    lines.append(f'# 共 {len(scene_files)} 个场景待渲染')
    lines.append('')
    
    for i, scene_file in enumerate(scene_files):
        scene_name = scene_file.stem
        lines.extend([
            f'# --- 场景 {i+1}: {scene_name} ---',
            f'print(f"渲染场景 {i+1}/{len(scene_files)}: {scene_name}")',
            f'scene_output = os.path.join(OUTPUT_DIR, "{scene_name}")',
            f'os.makedirs(scene_output, exist_ok=True)',
            f'scene.render.filepath = os.path.join(scene_output, "{scene_name}_")',
            f'bpy.ops.render.render(animation=True, write_still=True)',
            f'print(f"✅ {scene_name} 渲染完成")',
            '',
        ])
    
    lines.extend([
        'print(f"\\n🎉 全部渲染完成，输出目录: {OUTPUT_DIR}")',
    ])
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Blender渲染管线")
    parser.add_argument("--batch-dir", help="批量场景目录")
    parser.add_argument("--scene", help="单个场景JSON")
    parser.add_argument("--assets", help="资产索引JSON")
    parser.add_argument("--output", default="./renders", help="输出目录")
    parser.add_argument("--format", default="PNG", choices=["PNG", "MP4", "FFMPEG"])
    parser.add_argument("--resolution", default="1920x1080")
    parser.add_argument("--frames", default=None, help="帧范围 START:END")
    parser.add_argument("--render-engine", default="BLENDER_EEVEE_NEXT")
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--generate-only", action="store_true", help="仅生成脚本不执行")
    
    args = parser.parse_args()
    
    width, height = map(int, args.resolution.split("x"))
    
    config = {
        "resolution": [width, height],
        "fps": args.fps,
        "render_engine": args.render_engine,
    }
    
    if args.batch_dir:
        script = generate_render_script(args.batch_dir, {}, args.output, config)
        output_file = "batch_render.py"
        Path(output_file).write_text(script, encoding="utf-8")
        print(f"✅ 批量渲染脚本生成: {output_file}")
        print(f"   场景目录: {args.batch_dir}")
        print(f"   输出目录: {args.output}")
        
        if not args.generate_only:
            print(f"\\n执行命令:")
            print(f"blender --background --python {output_file}")
    
    elif args.scene:
        print(f"单场景渲染: {args.scene}")
        print(f"执行命令:")
        print(f"blender --background --python-expr \"import bpy; bpy.ops.render.render()\"")


if __name__ == "__main__":
    main()
