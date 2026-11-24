"""DEXPI 校验：用 pyDEXPI 加载每张 P&ID/BFD/PFD，统计对象数量并跑内置规则。

输出 bed/dexpi/dexpi-check.md 与 bed/dexpi/dexpi-check.json。
退出码：加载失败或存在 MANDATORY 级问题时为 1。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from pydexpi.loaders.public import load_xml_file
from pydexpi.validation import validate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "bed" / "dexpi"


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def counts(path: Path) -> Counter:
    tree = ET.parse(path)
    return Counter(local(el.tag) for el in tree.iter())


def main() -> int:
    sheets = sorted((ROOT / "pid").glob("*.xml")) + [
        ROOT / "process" / "BFD.xml",
        ROOT / "process" / "PFD.xml",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    rows, issues, failures = [], [], []
    for path in sheets:
        if not path.exists():
            continue
        name = path.relative_to(ROOT).as_posix()
        try:
            model = load_xml_file(path, strict=True)
        except Exception as exc:  # DEXPI 结构问题必须显式暴露
            failures.append({"file": name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        try:
            found = validate(model)
        except Exception as exc:
            failures.append({"file": name, "error": f"validate: {type(exc).__name__}: {exc}"})
            found = []
        c = counts(path)
        rows.append(
            {
                "file": name,
                "equipment": c["Equipment"],
                "piping_segments": c["PipingNetworkSegment"],
                "instruments": c["InstrumentationLoopFunction"],
                "issues": len(found),
                "mandatory": sum(
                    1 for i in found if i.level_of_recommendation.name == "MANDATORY"
                ),
            }
        )
        for i in found:
            issues.append(
                {
                    "file": name,
                    "rule": i.applied_rule_id,
                    "level": i.level_of_recommendation.name,
                    "description": i.short_description,
                    "components": i.affected_component_ids[:8],
                }
            )

    payload = {"sheets": rows, "issues": issues, "failures": failures}
    (OUT / "dexpi-check.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    lines = [
        "# DEXPI 校验报告",
        "",
        "工具：pyDEXPI 2.1.0（DEXPI 2.0.1 数据模型）+ 内置校验规则。",
        "",
        "| 图纸 | 设备 | 管段 | 仪表回路 | 问题 | 其中 MANDATORY |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['file']} | {r['equipment']} | {r['piping_segments']} | "
            f"{r['instruments']} | {r['issues']} | {r['mandatory']} |"
        )
    lines += ["", f"合计：{len(rows)} 张图纸，{len(issues)} 条规则问题，{len(failures)} 个加载错误。", ""]
    if failures:
        lines += ["## 加载失败", ""]
        for f in failures:
            lines.append(f"- `{f['file']}`：{f['error']}")
        lines.append("")
    if issues:
        lines += ["## 规则问题（前 50 条）", ""]
        for i in issues[:50]:
            lines.append(
                f"- `{i['file']}` [{i['level']}] {i['rule']}：{i['description']}"
            )
    (OUT / "dexpi-check.md").write_text("\n".join(lines), encoding="utf-8")

    mandatory = sum(r["mandatory"] for r in rows)
    print(f"sheets={len(rows)} issues={len(issues)} mandatory={mandatory} failures={len(failures)}")
    print(f"written: {OUT / 'dexpi-check.md'}")
    return 1 if failures or mandatory else 0


if __name__ == "__main__":
    sys.exit(main())
