"""把 DWSIM 收敛记录汇总成可读的 Markdown（BED 交付物之一）。"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "process" / "simulation-run.json"
OUT = ROOT / "bed" / "dwsim" / "simulation-summary.md"


def main() -> int:
    data = json.loads(RUN.read_text(encoding="utf-8"))
    case = (data.get("cases") or {}).get("design") or {}
    units = case.get("units") or []
    status = Counter(u.get("status", "unknown") for u in units)
    sim = case.get("simulator") or {}
    lines = [
        "# DWSIM 仿真结果摘要",
        "",
        f"- 模拟器：{sim.get('name', 'DWSIM')} {sim.get('version', '')}",
        f"- 物性方法：{sim.get('method', case.get('property_package', ''))}",
        f"- 收敛：{case.get('converged')}（{case.get('status')}，{case.get('iterations')} 次迭代）",
        f"- 运行时间：{case.get('run_at')}；记录工具：{case.get('tool')}",
        f"- 设备/单元：{len(units)} 个（" + "，".join(f"{k} {v}" for k, v in status.items()) + "）",
        "",
        "## 单元状态",
        "",
        "| 单元 | 类型 | 状态 | 收敛 | 依据 |",
        "|---|---|---|---|---|",
    ]
    for u in units:
        lines.append(
            f"| {u.get('id')} | {u.get('unit')} | {u.get('status')} | "
            f"{u.get('converged')} | {u.get('basis', '')} |"
        )
    lines += [
        "",
        "## 说明",
        "",
        "- 本摘要来自 `process/simulation-run.json` 中 DWSIM 9.0.5 的实际收敛记录。",
        "- 本机未安装 DWSIM 9.0.5（安装包 272 MB，当前网络约 11 KB/s，未完成下载），"
        "因此没有重新运行；重新运行的命令见 `bed/dwsim/README.md`。",
        "- 结果只覆盖 `process/simulation.yaml` 声明的范围：排除了 H101、U801、K701；"
        "aMDEA 为指定分割；PR 缺少有来源的 kij。",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"units={len(units)} converged={case.get('converged')} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
