"""生成 lng-terminal MANIFEST（从 bed/ 扫描）。"""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

BED = Path(__file__).resolve().parent.parent / "bed"
artifacts = []
for p in sorted(BED.rglob("*")):
    if p.is_file():
        h = hashlib.sha256(); h.update(p.read_bytes())
        artifacts.append({
            "path": p.relative_to(BED).as_posix(),
            "bytes": p.stat().st_size,
            "sha256_16": h.hexdigest()[:16],
        })

manifest = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "plant": "LNG export marine terminal (lng-terminal-1, 2 x 225,000 m3, 28 MTPA)",
    "site": "Kitimat, BC (reference site)",
    "level": "BED 方案级可用：用于方案比选与下一阶段设计输入，不用于施工采购许可或安全决策",
    "upstream": "ChemE-as-Code/process-library processes:lng-terminal-1",
    "artifacts": artifacts,
}
(BED / "MANIFEST.json").write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
)
md = [
    "# LNG Export Terminal BED 包清单",
    "",
    "生成时间：" + manifest["generated_at"],
    "",
    "**工厂**：LNG export marine terminal — 2 x 225,000 m3 full-containment tanks,"
    " 4 x 16 loading arms/berth, 28 MTPA rundown",
    "",
    "**上游**：ChemE-as-Code/process-library processes/lng-terminal-1",
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
print(f"MANIFEST: {BED / 'MANIFEST.md'} ({len(artifacts)} artifacts)")
