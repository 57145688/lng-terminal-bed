"""pyHazop 兼容工作表导出。

公开的 pyhazop 仓库（EbrahemAbdraboh/pyhazop）只是网页演示，没有可调用的分析包。
本脚本以 cheme 的 HAZOP 数据模型（safety/hazop/H-01/study.yaml）为数据源，
按 pyHazop/HAZOP 通用列输出 CSV 与 Markdown 初稿：节点、参数、引导词、原因、
后果、现有 safeguard、初始/剩余风险、建议措施、状态。

输出：bed/hazop/hazop-worksheet.csv、bed/hazop/hazop-draft.md
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "safety" / "hazop" / "H-01" / "study.yaml"
OUT = ROOT / "bed" / "hazop"


def band(risk, key):
    try:
        return risk[key][0]["band"]["value"]
    except (KeyError, IndexError, TypeError):
        return ""


def main() -> int:
    study = yaml.safe_load(STUDY.read_text(encoding="utf-8"))
    rows = []
    for node in study.get("nodes", []):
        for dev in node.get("deviations", []):
            for sc in dev.get("scenarios", []):
                risk = sc.get("risk") or {}
                rows.append(
                    {
                        "node": node.get("id", ""),
                        "intent": " ".join((node.get("design_intent") or "").split())[:180],
                        "parameter": dev.get("parameter", ""),
                        "guide_word": dev.get("guide_word", ""),
                        "cause": " ".join((sc.get("cause") or "").split()),
                        "consequence": " ".join((sc.get("consequence") or "").split()),
                        "safeguards": " | ".join(sc.get("safeguards") or []),
                        "risk_initial": band(risk, "initial"),
                        "risk_residual": band(risk, "residual"),
                        "status": sc.get("status", ""),
                        "by": sc.get("by", ""),
                    }
                )

    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with (OUT / "hazop-worksheet.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(r["risk_initial"] or "未评级" for r in rows)
    md = [
        "# HAZOP 初稿（BED 方案级）",
        "",
        f"来源：`{STUDY.relative_to(ROOT)}`（{study.get('title', 'HAZOP')}），"
        f"{len(study.get('nodes', []))} 个节点、{len(rows)} 个偏差场景。",
        "",
        "**状态：draft（草案），未经 HAZOP 团队评审，不得作为安全决策依据。**",
        "",
        "## 初始风险分布",
        "",
        "| 风险等级 | 场景数 |",
        "|---|---:|",
    ]
    for level, n in sorted(counts.items()):
        md.append(f"| {level} | {n} |")
    md += [
        "",
        "## 工作表（前 40 行，完整见 hazop-worksheet.csv）",
        "",
        "| 节点 | 参数 | 引导词 | 原因 | 后果 | 初始风险 | 剩余风险 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows[:40]:
        cause = r["cause"].replace("|", "/")[:160]
        cons = r["consequence"].replace("|", "/")[:200]
        md.append(
            f"| {r['node']} | {r['parameter']} | {r['guide_word']} | {cause} | "
            f"{cons} | {r['risk_initial']} | {r['risk_residual']} |"
        )
    md += [
        "",
        "## 使用边界",
        "",
        "- 本初稿由 AI 辅助生成并经 cheme validate 校验，未召开正式 HAZOP 会议。",
        "- 风险矩阵来自 `safety/risk-matrix.yaml`；SIL 定级、LOPA、定量风险分析均未开展。",
        "- 详细设计阶段必须由多专业团队逐节点复核，并关闭 `cheme safety hazop check` 的未决项。",
    ]
    (OUT / "hazop-draft.md").write_text("\n".join(md), encoding="utf-8")
    print(f"scenarios={len(rows)} -> {OUT / 'hazop-draft.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
