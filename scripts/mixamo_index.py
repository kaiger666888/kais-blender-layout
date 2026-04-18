#!/usr/bin/env python3
"""
Mixamo 资产索引工具
扫描FBX文件，提取模型/动作元数据，建立资产索引
"""

import argparse
import json
import os
import sys
from pathlib import Path


def scan_directory(directory: str) -> dict:
    """扫描目录，分类FBX文件为模型/动作/环境"""
    models = []
    animations = []
    environments = []
    
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"❌ 目录不存在: {directory}", file=sys.stderr)
        sys.exit(1)
    
    for fbx_file in sorted(dir_path.rglob("*.fbx")):
        rel_path = fbx_file.relative_to(dir_path)
        name = fbx_file.stem
        
        # 简单分类规则（基于路径和文件名）
        path_lower = str(rel_path).lower()
        
        if "anim" in path_lower or "motion" in path_lower or "walk" in name.lower() or "run" in name.lower() or "idle" in name.lower():
            animations.append({
                "name": name,
                "file": str(rel_path),
                "type": classify_animation(name),
                "frames": None,  # 需要Blender解析
                "fps": 24
            })
        elif "env" in path_lower or "scene" in path_lower or "ground" in path_lower or "building" in path_lower:
            environments.append({
                "name": name,
                "file": str(rel_path)
            })
        else:
            models.append({
                "name": name,
                "file": str(rel_path),
                "type": classify_model(name, path_lower),
                "skeleton": "mixamo"
            })
    
    return {
        "models": models,
        "animations": animations,
        "environments": environments,
        "meta": {
            "source_dir": str(dir_path),
            "total_files": len(models) + len(animations) + len(environments)
        }
    }


def classify_animation(name: str) -> str:
    """简单分类动画类型"""
    name_lower = name.lower()
    if any(w in name_lower for w in ["walk", "run", "sprint", "jump"]):
        return "locomotion"
    elif any(w in name_lower for w in ["attack", "hit", "slash", "punch"]):
        return "combat"
    elif any(w in name_lower for w in ["idle", "stand", "breathe"]):
        return "idle"
    elif any(w in name_lower for w in ["die", "fall", "death"]):
        return "death"
    elif any(w in name_lower for w in ["talk", "speak", "gesture"]):
        return "gesture"
    return "other"


def classify_model(name: str, path: str) -> str:
    """简单分类模型类型"""
    name_lower = name.lower()
    if any(w in name_lower for w in ["char", "hero", "warrior", "knight", "girl", "boy", "man", "woman", "zombie", "robot"]):
        return "character"
    elif any(w in name_lower for w in ["weapon", "sword", "gun", "bow", "shield"]):
        return "weapon"
    elif any(w in name_lower for w in ["chest", "table", "chair", "crate", "barrel", "pot"]):
        return "prop"
    return "other"


def main():
    parser = argparse.ArgumentParser(description="Mixamo资产索引工具")
    parser.add_argument("command", choices=["scan"], help="执行命令")
    parser.add_argument("--dir", required=True, help="Mixamo素材目录")
    parser.add_argument("--output", default="asset_library.json", help="输出JSON文件")
    
    args = parser.parse_args()
    
    if args.command == "scan":
        index = scan_directory(args.dir)
        
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 索引完成")
        print(f"   模型: {len(index['models'])}")
        print(f"   动作: {len(index['animations'])}")
        print(f"   环境: {len(index['environments'])}")
        print(f"   总计: {index['meta']['total_files']}")
        print(f"   输出: {args.output}")


if __name__ == "__main__":
    main()
