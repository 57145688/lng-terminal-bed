"""LNG export terminal 工艺摘要：从 flowsheet / equipment-list / line-list 提取关键数据。

lng-terminal-1 用 CoolProp + GERG-2008 的 scripts/terminal_sizing.py 计算流股，
没有 DWSIM。本脚本生成 bed/dwsim/terminal-summary.md，汇总工厂规模、流股、设备和管线。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BED = ROOT / "bed" / "dwsim"


def parse_streams(flowsheet: dict) -> list[dict]:
    """从 flowsheet 提取各 case 下的 stream state。"""
    streams_out = []
    design = flowsheet.get("streams", [])
    default_case_id = "average"

    for s in design:
        sid = s.get("id", "?")
        title = s.get("title", sid)
        links = s.get("links", [])
        link_from = link_to = ""
        for l in links:
            if isinstance(l, dict):
                if l.get("role") == "from_equipment":
                    link_from = str(l.get("ref", ""))
                elif l.get("role") == "to_equipment":
                    link_to = str(l.get("ref", ""))
        state = s.get("state", {})
        cases = state.get("cases", {}) or {}
        # default case or first
        cdata = cases.get(default_case_id)
        if cdata is None and cases:
            cdata = list(cases.values())[0]
        elif cdata is None:
            cdata = state

        def v(key):
            d = cdata.get(key, {}) if isinstance(cdata, dict) else {}
            if isinstance(d, dict):
                return d.get("value", "?")
            return d

        composition = ""
        comp = cdata.get("composition", {}) if isinstance(cdata, dict) else {}
        if isinstance(comp, dict):
            vals = comp.get("values", {})
            if vals:
                composition = ", ".join(f"{k} {v:.4f}" for k, v in list(vals.items())[:6])

        streams_out.append({
            "id": sid,
            "title": title,
            "from": link_from,
            "to": link_to,
            "pressure_kPa": v("pressure"),
            "temperature_K": v("temperature"),
            "flow_kgh": v("flow"),
            "composition": composition,
        })
    return streams_out


def main() -> int:
    flowsheet = yaml.safe_load((ROOT / "process" / "flowsheet.yaml").read_text(encoding="utf-8"))
    equip = yaml.safe_load((ROOT / "equipment" / "equipment-list.yaml").read_text(encoding="utf-8"))
    lines = yaml.safe_load((ROOT / "piping" / "line-list.yaml").read_text(encoding="utf-8"))
    plant = yaml.safe_load((ROOT / "plant.yaml").read_text(encoding="utf-8"))

    # --- 工厂规模 ---
    name = plant.get("name", "?")
    desc = plant.get("description", "")
    # 从描述提取容量
    capacity_mtpa = re.search(r"(\d+[\d.,]*)\s*MTPA", desc)
    if capacity_mtpa:
        capacity = f"{capacity_mtpa.group(1)} MTPA"
    else:
        capacity = "reference"

    tanks = [e for e in (equip.get("equipment") or []) if e.get("type") == "Tank"
             and "LNG" in (e.get("service") or "")]
    pumps = [e for e in (equip.get("equipment") or []) if "pump" in (e.get("type", "")).lower()]
    compressors = [e for e in (equip.get("equipment") or []) if "ompress" in (e.get("type", "")).lower()]

    # --- 管线 ---
    all_lines = lines.get("lines") or []
    by_dn = {}
    by_fluid = {}
    for ln in all_lines:
        dn_str = ln.get("nominal_diameter", "?")
        fluid = ln.get("fluid", "?")
        by_dn[dn_str] = by_dn.get(dn_str, 0) + 1
        by_fluid[fluid] = by_fluid.get(fluid, 0) + 1

    # --- 流股 ---
    streams = parse_streams(flowsheet)
    cases = [c["id"] for c in flowsheet.get("cases", [])]
    feeds = [f["id"] for f in flowsheet.get("feeds", [])]
    products = [p["id"] for p in flowsheet.get("products", [])]

    BED.mkdir(parents=True, exist_ok=True)

    md_lines = [
        f"# {name} — Terminal Summary",
        "",
        f"**Plant**: {name}",
        f"**Capacity**: {capacity}",
        f"**Cases (flowsheet)**: {', '.join(cases)}",
        f"**Stage**: {plant.get('stage', '?')}",
        "",
        "## 设计输入边界",
        f"- Feeds: {', '.join(feeds)}",
        f"- Products: {', '.join(products)}",
        f"- **物料包**: GERG-2008 (CoolProp reference EOS), 非 Aspen/Peng-Robinson",
        f"- **无 DWSIM simulation.yaml**；流股由 scripts/terminal_sizing.py 生成",
        f"- **单位**: kPa(a) / K / kg/h",
        "",
        "## 主要设备",
        f"| 类型 | 数量 | 代表标签 |",
        "|---|---:|---|",
        f"| LNG 储罐 (225,000 m³) | {len(tanks)} | {', '.join(t['tag'] for t in tanks)} |",
        f"| 泵 (含内泵) | {len(pumps)} | {pumps[0]['tag'] if pumps else ''} ... |",
        f"| BOG 压缩机 | {len(compressors)} | {compressors[0]['tag'] if compressors else ''} ... |",
        f"| **合计** | **{len(equip.get('equipment') or [])}** | — |",
        "",
        "## 管线分布 (by fluid)",
        f"| 流体 | 条数 |",
        "|---|---:|",
    ]
    for f, cnt in sorted(by_fluid.items(), key=lambda x: -x[1]):
        md_lines.append(f"| {f} | {cnt} |")
    md_lines += [
        "",
        "## 管线口径分布",
        f"| DN | 条数 |",
        "|---|---:|",
    ]
    for dn, cnt in sorted(by_dn.items(), key=lambda x: x[0]):
        md_lines.append(f"| {dn} | {cnt} |")
    md_lines += [
        "",
        "## 关键流股 (case: average)",
        f"| Stream | 描述 | P kPa(a) | T K | Flow kg/h | Composition |",
        "|---|---|---:|---:|---:|---|",
    ]
    for s in streams[:30]:
        md_lines.append(
            f"| {s['id']} | {s['title'][:45]} | {s['pressure_kPa']} |"
            f" {s['temperature_K']} | {s['flow_kgh']} | {s['composition'][:55]} |"
        )
    md_lines += [
        "",
        "> 备注：所有 state 来自 `flowsheet.yaml` 的 provenance `scripts/terminal_sizing.py`，"
        "source=GERG-2008 (CoolProp)。P&ID 见 bed/pid/*.svg，三维见 bed/cad/ammonia-bed.step。",
    ]

    (BED / "terminal-summary.md").write_text("\n".join(md_lines), encoding="utf-8")

    json_out = {
        "plant": name,
        "capacity": capacity,
        "cases": cases,
        "equipment_count": len(equip.get("equipment") or []),
        "lines_count": len(all_lines),
        "streams_count": len(streams),
        "streams": streams,
        "lines_by_fluid": by_fluid,
        "lines_by_dn": by_dn,
    }
    (BED / "terminal-summary.json").write_text(
        json.dumps(json_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"terminal_summary: {len(streams)} streams, {len(all_lines)} lines, "
          f"{len(equip.get('equipment') or [])} equipment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
