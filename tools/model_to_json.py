"""把 cheme 生成的三维布局压缩成 FreeCAD 可读的 JSON。

只保留设备包围盒/尺寸与管线折点，避免 FreeCAD 侧依赖 PyYAML。
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "layout" / "plant-model.yaml"
OUT = ROOT / "bed" / "cad" / "plant-model.json"


def main() -> None:
    model = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    equipment = []
    for item in model.get("equipment", []):
        equipment.append(
            {
                "id": item["id"],
                "family": item.get("family", "box"),
                "bbox": item.get("bbox"),
                "dimensions": item.get("dimensions", {}),
            }
        )
    pipes = []
    for item in model.get("pipes", []):
        pipes.append(
            {
                "id": item["id"],
                "line": item.get("line"),
                "dn": item.get("dn", 0),
                "points": item.get("points", []),
            }
        )
    payload = {
        "units": "m",
        "site": model.get("site", {}),
        "equipment": equipment,
        "pipes": pipes,
        "buildings": model.get("buildings", []),
        "racks": model.get("racks", []),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"equipment={len(equipment)} pipes={len(pipes)} -> {OUT}")


if __name__ == "__main__":
    main()
