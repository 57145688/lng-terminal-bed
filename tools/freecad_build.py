"""在 FreeCAD 中由 cheme 布局生成三维设备与管线，并导出 STEP。

用法（无界面）：
  "D:\\Program Files\\FreeCAD 1.0\\bin\\freecadcmd.exe" tools/freecad_build.py

输入：bed/cad/plant-model.json（tools/model_to_json.py 生成）
输出：bed/cad/ammonia-bed.FCStd、bed/cad/ammonia-bed.step、bed/cad/freecad-report.json

说明：ProcessWB / PipeFeatures 未检索到可用的公开发行版；本脚本用 FreeCAD Part
工作台实现等价的设备实体、管线实体与分组（Equipment / Piping / Structures），
对象名保留 PF_<line>_<segment> 前缀，便于后续接入上述工作台。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import FreeCAD as App
import Part

ROOT = Path(os.environ.get("BED_ROOT") or Path.cwd()).resolve()
IN = ROOT / "bed" / "cad" / "plant-model.json"
OUT = IN.parent
print("FREECAD_START", str(ROOT), flush=True)


def vec(p):
    return App.Vector(float(p[0]), float(p[1]), float(p[2]))


def cylinder_between(p1, p2, radius):
    a, b = vec(p1), vec(p2)
    direction = b - a
    if direction.Length < 1e-6:
        return None
    return Part.makeCylinder(radius, direction.Length, a, direction.normalize())


def equipment_shape(item):
    bbox = item.get("bbox")
    if not bbox or len(bbox) != 6:
        return None
    x0, y0, z0, x1, y1, z1 = (float(v) for v in bbox)
    dims = item.get("dimensions") or {}
    family = (item.get("family") or "").lower()
    if family in {"vessel", "column", "reactor"} and dims.get("diameter") and dims.get("height"):
        r = float(dims["diameter"]) / 2.0
        h = float(dims["height"])
        return Part.makeCylinder(r, h, App.Vector((x0 + x1) / 2, (y0 + y1) / 2, z0))
    dx, dy, dz = max(x1 - x0, 0.2), max(y1 - y0, 0.2), max(z1 - z0, 0.2)
    return Part.makeBox(dx, dy, dz, App.Vector(x0, y0, z0))


def main():
    data = json.loads(IN.read_text(encoding="utf-8"))
    print("FREECAD_DATA", len(data.get("equipment", [])), flush=True)
    doc = App.newDocument("AmmoniaBED")
    print("FREECAD_DOC", doc.Name, flush=True)
    groups = {
        "Equipment": doc.addObject("App::DocumentObjectGroup", "Equipment"),
        "Piping": doc.addObject("App::DocumentObjectGroup", "Piping"),
        "Structures": doc.addObject("App::DocumentObjectGroup", "Structures"),
    }
    features = []

    def add(name, shape, group):
        if shape is None:
            return
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        groups[group].addObject(obj)
        features.append(obj)

    site = data.get("site") or {}
    w = float(site.get("width") or 360.0)
    d = float(site.get("depth") or 220.0)
    add("SITE_GROUND", Part.makeBox(w, d, 0.2, App.Vector(0, 0, -0.2)), "Structures")

    for item in data.get("equipment", []):
        add(f"EQ_{item['id']}", equipment_shape(item), "Equipment")

    pipes = 0
    segments = 0
    for pipe in data.get("pipes", []):
        points = pipe.get("points") or []
        dn = float(pipe.get("dn") or 50)
        radius = max(dn / 2000.0, 0.02)
        solids = []
        for p1, p2 in zip(points, points[1:]):
            solid = cylinder_between(p1, p2, radius)
            if solid is not None:
                solids.append(solid)
        if solids:
            name = f"PF_{str(pipe.get('line') or pipe['id']).replace('/', '_')}_{pipe['id'].split('/')[-1]}_DN{int(dn)}"
            add(name, Part.makeCompound(solids), "Piping")
            pipes += 1
            segments += len(solids)

    for building in data.get("buildings", []):
        bbox = building.get("bbox")
        if bbox and len(bbox) == 6:
            x0, y0, z0, x1, y1, z1 = (float(v) for v in bbox)
            add(
                f"BLDG_{building.get('id', 'x')}",
                Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0)),
                "Structures",
            )

    doc.recompute()
    step = OUT / "ammonia-bed.step"
    fcstd = OUT / "ammonia-bed.FCStd"
    Part.export(features, str(step))
    doc.saveAs(str(fcstd))
    for backup in OUT.glob("*.FCBak"):
        backup.unlink(missing_ok=True)
    report = {
        "equipment": len(data.get("equipment", [])),
        "pipe_objects": pipes,
        "pipe_segments": segments,
        "step": str(step),
        "step_bytes": step.stat().st_size if step.exists() else 0,
    }
    (OUT / "freecad-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("FREECAD_OK", json.dumps(report, ensure_ascii=False))


main()
