"""BED 流水线编排：LNG export terminal (lng-terminal-1)

适配 terminal 工艺（无 DWSIM simulation、flowsheet 单位 kPa(a)/K/kg/h、5 个 HAZOP study）。
用法（在 lng-terminal-bed 根目录）：
  python tools/run_pipeline.py            # 全部
  python tools/run_pipeline.py --skip-cad # 跳过 FreeCAD
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BED = ROOT / "bed"
PY = sys.executable
CHEME = shutil.which("cheme") or str(ROOT.parent / ".venv" / "Scripts" / "cheme.exe")
FREECAD = os.environ.get(
    "FREECAD_CMD", r"D:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe"
)


def run(name, cmd, cwd=ROOT, check=True, env=None):
    print(f"\n=== {name} ===", flush=True)
    print("$", " ".join(str(c) for c in cmd), flush=True)
    proc = subprocess.run(
        [str(c) for c in cmd], cwd=str(cwd), text=True, encoding="utf-8",
        errors="replace", env={**os.environ, **(env or {})},
    )
    print(f"[{name}] exit={proc.returncode}", flush=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"{name} failed with {proc.returncode}")
    return proc.returncode


def sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-cad", action="store_true")
    args = ap.parse_args()

    # --- 1. cheme validate 基线 ---
    run("cheme validate", [CHEME, "validate"])

    # --- 2. DEXPI 校验（8 张 P&ID + BFD/PFD） ---
    run("DEXPI check", [PY, ROOT / "tools" / "dexpi_check.py"])

    # --- 3. 流股表 ---
    (BED / "dwsim").mkdir(parents=True, exist_ok=True)
    with (BED / "dwsim" / "stream-table.csv").open("w", encoding="utf-8", newline="") as fp:
        subprocess.run(
            [CHEME, "process", "streams", "--csv"], cwd=str(ROOT),
            stdout=fp, text=True, encoding="utf-8",
        )

    # --- 4. Terminal 工艺摘要（从 flowsheet + line-list + equipment-list）---
    run("Terminal summary", [PY, ROOT / "tools" / "terminal_summary.py"])

    # --- 5. LCA ---
    run("LCA (cheme, open factors)", [CHEME, "assess", "lca", "--write"], check=False)

    # --- 6. PSI 应力初算（需适配 LNG terminal 单位与流体）---
    run("PSI batch stress", [PY, ROOT / "tools" / "psi_batch.py"])

    # --- 7. FreeCAD 三维 ---
    if not args.skip_cad:
        run("layout -> JSON", [PY, ROOT / "tools" / "model_to_json.py"])
        if Path(FREECAD).exists():
            run("FreeCAD STEP", [FREECAD, ROOT / "tools" / "freecad_build.py"],
                env={"BED_ROOT": str(ROOT)})
        else:
            print(f"FreeCAD not found at {FREECAD}; skipped", flush=True)

    # --- 8. HAZOP 导出（所有 H-0* study）---
    run("HAZOP export", [PY, ROOT / "tools" / "hazop_export.py"])

    # --- 9. HAZOP report（遍历 H-01..H-05）---
    hazon_ids = sorted(
        d.name for d in (ROOT / "safety" / "hazop").iterdir() if d.is_dir()
    ) if (ROOT / "safety" / "hazop").exists() else ["H-01"]

    for hid in hazon_ids:
        run(f"HAZOP report {hid}", [CHEME, "safety", "hazop", "report", hid], check=False)
        src_md = ROOT / "build" / "hazop" / f"{hid}.md"
        src_html = ROOT / "build" / "hazop" / f"{hid}.html"
        dst_md = BED / "hazop" / f"{hid}-full-report.md"
        dst_html = BED / "hazop" / f"{hid}-full-report.html"
        if src_md.exists():
            shutil.copy2(src_md, dst_md)
        if src_html.exists():
            shutil.copy2(src_html, dst_html)

    # --- 10. 复制上游原始文件 ---
    copies = [
        (ROOT / "plant.yaml", BED / "plant.yaml"),
        (ROOT / "DESIGN.md", BED / "DESIGN.md"),
        (ROOT / "README.md", BED / "README.md"),
        (ROOT / "lca" / "results.md", BED / "lca" / "cheme-lca-results.md"),
        (ROOT / "lca" / "results.csv", BED / "lca" / "cheme-lca-results.csv"),
        (ROOT / "lca" / "inventory.csv", BED / "lca" / "cheme-lca-inventory.csv"),
    ]
    for src, dst in copies:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # --- 11. 渲染 P&ID ---
    (BED / "pid").mkdir(parents=True, exist_ok=True)
    for pid_xml in sorted(glob.glob(str(ROOT / "pid" / "*.xml"))):
        pid_id = Path(pid_xml).stem
        run(f"render {pid_id}", [CHEME, "render", pid_xml, "-o", str(BED / "pid" / f"{pid_id}.svg")],
            check=False)

    # --- 12. MANIFEST ---
    artifacts = []
    for path in sorted(BED.rglob("*")):
        if path.is_file():
            artifacts.append(
                {"path": path.relative_to(BED).as_posix(), "bytes": path.stat().st_size,
                 "sha256_16": sha(path)}
            )
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plant": "LNG export marine terminal (lng-terminal-1, 2 x 225,000 m3, 28 MTPA)",
        "site": "Kitimat, BC (reference site)",
        "level": "BED 方案级可用：用于方案比选与下一阶段设计输入，不用于施工、采购或安全决策",
        "upstream": "ChemE-as-Code/process-library process:lng-terminal-1",
        "requires": "cheme-as-code>=1.5",
        "artifacts": artifacts,
    }
    (BED / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md = [
        "# LNG Export Terminal BED 包清单",
        "",
        f"生成时间：{manifest['generated_at']}",
        "",
        f"**工厂**：LNG export marine terminal — 2 × 225,000 m³ full-containment tanks,"
        f" 4 × 16″ loading arms/berth, 28 MTPA rundown",
        "",
        f"**上游**：ChemE-as-Code/process-library `processes/lng-terminal-1`",
        "",
        "> 定位：**BED 方案级可用**。用于路线比选、规模论证与下一阶段设计输入；"
        "不用于施工、采购、许可或安全决策。",
        "",
        "| 文件 | 大小 (KB) | SHA256 前 16 位 |",
        "|---|---:|---|",
    ]
    for a in artifacts:
        if a["path"] == "MANIFEST.json":
            continue
        md.append(f"| {a['path']} | {a['bytes'] / 1024:.1f} | `{a['sha256_16']}` |")
    (BED / "MANIFEST.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nMANIFEST: {BED / 'MANIFEST.md'} ({len(artifacts)} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
