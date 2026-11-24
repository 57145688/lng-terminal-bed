"""管道应力初算：为关键管线生成 PSI（Pipe Stress Infinity）输入并批量运行。

PSI 0.0.1 在当前 Python/Pint 组合下求解器存在上游缺陷（loads.flocal 形状错误），
因此本脚本同时给出 B31.1 的保守上限筛查（完全约束热伸长 + 内压），
报告中明确区分「PSI 运行状态」与「保守筛查值」。BED 方案级只用于识别
需要详细柔性分析的管线，不作为设计结论。
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "bed" / "psi"
PSI = Path(os.environ.get("PSI_EXE", ROOT.parent / ".venv-psi" / "Scripts" / "psi.exe"))
CASES = OUT / "cases"

# DN -> (OD mm, wall mm, NPS inch)
PIPE_TABLE = {
    50: (60.3, 3.91, 2), 80: (88.9, 5.49, 3), 100: (114.3, 6.02, 4),
    150: (168.3, 7.11, 6), 200: (219.1, 8.18, 8), 250: (273.0, 9.27, 10),
    300: (323.9, 10.31, 12), 350: (355.6, 11.13, 14), 400: (406.4, 12.70, 16),
    450: (457.0, 14.27, 18), 500: (508.0, 15.09, 20), 600: (610.0, 17.48, 24),
    700: (711.0, 19.05, 28), 800: (813.0, 20.62, 32), 900: (914.0, 22.23, 36),
    1000: (1016.0, 24.61, 40), 1200: (1219.0, 27.79, 48), 1400: (1422.0, 31.75, 54),
    1600: (1626.0, 34.93, 64),
}
E_MPA, ALPHA, SC_MPA, SH_MPA = 200_000.0, 12e-6, 138.0, 130.0


def dn_number(text: str) -> int:
    digits = "".join(ch for ch in str(text) if ch.isdigit())
    return int(digits) if digits else 100


def pipe_props(dn: int):
    if dn in PIPE_TABLE:
        return PIPE_TABLE[dn]
    od, t, nps = 1.05 * dn, max(6.0, 0.025 * dn), max(2, round(dn / 25))
    return od, t, nps


def line_lengths(model) -> dict:
    out = {}
    for pipe in model.get("pipes", []):
        pts = pipe.get("points") or []
        length = sum(
            math.dist(a, b) for a, b in zip(pts, pts[1:])
        )
        out[pipe.get("line")] = max(out.get(pipe.get("line"), 0.0), length)
    return out


def stream_conditions(flowsheet) -> dict:
    """从 flowsheet streams 读取 stream -> line 的压力/温度。

    兼容两种结构：
    - reaction 工艺：state.design.pressure/temperature.value
    - terminal 工艺：state.average.pressure/temperature.value
    """
    out = {}
    for stream in flowsheet.get("streams", []):
        state = stream.get("state") or {}
        # state.average 优先（terminal 工艺），fallback state.cases.average，再 fallback state.design
        src = (
            state.get("average")
            or (state.get("cases") or {}).get("average")
            or state.get("design")
            or {}
        )
        for link in stream.get("links", []):
            if link.get("target") != "line":
                continue
            out[link["ref"]] = {
                "pressure_kpa": (src.get("pressure") or {}).get("value"),
                "temperature_k": (src.get("temperature") or {}).get("value"),
                "stream": stream.get("id"),
            }
    return out


def psi_input(line, dn, nps, length_m, p_bar, t_c):
    if nps > 48 or t_c > 500:
        return None
    schedule = "40" if nps <= 24 else "STD"
    x = max(length_m * 0.7, 3.0)
    z = max(length_m * 0.3, 1.0)
    return f"""# PSI input generated for {line}, DN{dn}, B31.1 screening.
app.units.set_user_units('si')
mdl = Model('{line}')
pipe = Pipe.from_file('pipe', '{nps}', '{schedule}')
mat = Material.from_file('mat', 'A53A', 'B31.1')
Point(10)
run1 = Run(20, {x:.3f}, 0, 0, section=pipe, material=mat)
run2 = Run(30, 0, 0, {z:.3f}, section=pipe, material=mat)
Anchor('A1', 10).apply([run1, run2])
Z('G1', 30).apply([run1, run2])
Weight('W1', 1).apply([run1, run2])
Pressure('P1', 1, {p_bar:.2f}).apply([run1, run2])
Thermal('T1', 1, {t_c + 273.15:.2f}, 293.15).apply([run1, run2])
l1 = LoadCase('l1', 'sus', [Weight, Pressure], [1, 1])
l2 = LoadCase('l2', 'exp', [Thermal], [1])
B31167('B31.1').apply([run1, run2])
mdl.analyze()
Stresses('r1', [l1]).to_screen()
Stresses('r2', [l2]).to_screen()
"""


ROW = re.compile(
    r"^\s*(\d+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+"
    r"(-?[\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s*$",
    re.M,
)


def parse_stress(text):
    vals = []
    for m in ROW.finditer(text):
        try:
            vals.append((float(m.group(7)), float(m.group(8))))
        except ValueError:
            continue
    if not vals:
        return None
    code_psi, ratio = max(vals, key=lambda x: x[1])
    return {
        "psi_max_code_psi": code_psi,
        "psi_max_code_mpa": round(code_psi * 0.00689476, 2),
        "psi_max_ratio": ratio,
    }


def screening(dn, length_m, p_bar, t_c):
    od, wall, _ = pipe_props(dn)
    p_mpa = p_bar / 10.0
    hoop = p_mpa * od / (2 * wall)
    axial_p = p_mpa * od / (4 * wall)
    dt = max(t_c - 20.0, 0.0)
    thermal = E_MPA * ALPHA * dt           # fully restrained upper bound
    util_sus = axial_p / (0.75 * SH_MPA)
    util_exp = thermal / (1.25 * SC_MPA + 0.25 * SH_MPA)
    return {
        "od_mm": od, "wall_mm": wall, "hoop_mpa": hoop,
        "axial_pressure_mpa": axial_p, "thermal_restrained_mpa": thermal,
        "util_sustained": util_sus, "util_expansion_bound": util_exp,
        "verdict": "需详细柔性分析" if max(util_sus, util_exp) > 1.0 else "初算通过",
    }


def main() -> int:
    lines_doc = yaml.safe_load((ROOT / "piping" / "line-list.yaml").read_text(encoding="utf-8"))
    model = yaml.safe_load((ROOT / "layout" / "plant-model.yaml").read_text(encoding="utf-8"))
    flowsheet = yaml.safe_load((ROOT / "process" / "flowsheet.yaml").read_text(encoding="utf-8"))
    lengths = line_lengths(model)
    conditions = stream_conditions(flowsheet)

    rows = []
    for line in lines_doc.get("lines", []):
        number = line["number"]
        dn = dn_number(line.get("nominal_diameter"))
        c = conditions.get(number, {})
        p_kpa = c.get("pressure_kpa") or 500.0
        t_k = c.get("temperature_k") or 323.15
        p_bar = max(1.1 * p_kpa / 100.0, 5.0)
        t_c = max(t_k - 273.15, 20.0) + 25.0
        rows.append(
            {
                "line": number, "dn": dn, "fluid": line.get("fluid"),
                "length_m": round(lengths.get(number, 30.0), 2),
                "p_bar": round(p_bar, 1), "t_c": round(t_c, 1),
                "stream": c.get("stream"),
            }
        )
    rows.sort(key=lambda r: (r["dn"] / 100 + r["p_bar"] / 20 + r["t_c"] / 100), reverse=True)
    eligible = [r for r in rows if r["dn"] <= 1200][:8]
    large = [r for r in rows if r["dn"] > 1200][:4]
    rows = sorted(eligible + large, key=lambda r: (r["dn"] / 100 + r["p_bar"] / 20 + r["t_c"] / 100), reverse=True)

    CASES.mkdir(parents=True, exist_ok=True)
    results = []
    for r in rows:
        props = screening(r["dn"], r["length_m"], r["p_bar"], r["t_c"])
        inp = CASES / f"{r['line']}.inp"
        nps = pipe_props(r["dn"])[2]
        text = psi_input(
            r["line"], r["dn"], nps, r["length_m"], r["p_bar"], r["t_c"]
        )
        status, psi = "psi-section-unavailable", {}
        if text is None:
            status = "psi-section-unavailable" if nps > 48 else "psi-temperature-out-of-range"
            inp.write_text(
                f"# DN {r['dn']} (NPS {nps}, T {r['t_c']} C) 超出 PSI 内置管表/材料温度范围，"
                "见 B31.1 保守筛查。",
                encoding="utf-8",
            )
        else:
            inp.write_text(text, encoding="utf-8")
            if PSI.exists():
                proc = subprocess.run(
                    [str(PSI), str(inp)], capture_output=True, text=True, timeout=180
                )
                out = proc.stdout + proc.stderr
                (CASES / f"{r['line']}.out").write_text(out, encoding="utf-8")
                parsed = parse_stress(out)
                if "Traceback" in out or proc.returncode != 0:
                    status = "psi-failed"
                elif parsed:
                    status = "psi-ok"
                    psi = parsed
                else:
                    status = "psi-no-result"
            else:
                status = "psi-not-installed"
        rec = {**r, **props, "psi_status": status, **psi}
        if psi:
            rec["verdict"] = (
                "PSI: 需详细分析" if psi["psi_max_ratio"] > 1.0 else "PSI: 初算通过"
            )
        results.append(rec)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stress-results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md = [
        "# 管道应力初算报告（BED 方案级）",
        "",
        f"PSI 可执行文件：`{PSI}`；关键管线 {len(results)} 条（按 DN、压力、温度排序）。",
        "",
        "**工具状态**：PSI 0.0.1 对 NPS ≤ 48、设计温度 ≤ 500 ℃ 的管线可完成 B31.1 计算；"
        "超出 PSI 内置管表或碳钢材料温度范围的大口径高温管线，标为 "
        "`psi-section-unavailable` / `psi-temperature-out-of-range`，改用保守上限。"
        "两类结果都只用于筛查。",
        "",
        "| 管线 | DN | 流体 | 长度 m | 设计压力 bar | 设计温度 °C | PSI CODE MPa | PSI RATIO | 保守热上限 MPa | 结论 | PSI 状态 |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        md.append(
            f"| {r['line']} | {r['dn']} | {r['fluid']} | {r['length_m']} | {r['p_bar']} | "
            f"{r['t_c']} | {r.get('psi_max_code_mpa', '')} | {r.get('psi_max_ratio', '')} | "
            f"{r['thermal_restrained_mpa']:.0f} | {r['verdict']} | {r['psi_status']} |"
        )
    md += [
        "",
        "## 使用边界",
        "",
        "- 本报告只用于 BED 方案级：识别高温、大口径、高压管线是否需要详细柔性分析。",
        "- 完全约束热伸长是上限；真实管系通过弯头、膨胀节、支吊架释放，PSI/CAESAR 详细分析后才能判定。",
        "- 未计入风、地震、水锤、两相流、冷紧、支架摩擦与法兰泄漏。",
        "- 设计压力按 1.1 × 操作压力、设计温度按操作温度 +25 K 假设，需由工艺专业确认。",
    ]
    (OUT / "stress-report.md").write_text("\n".join(md), encoding="utf-8")
    print(f"lines={len(results)} -> {OUT / 'stress-report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
