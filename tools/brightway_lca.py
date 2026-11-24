"""用 Brightway 2.5（bw2data/bw2calc）计算天然气制氨 BED 的筛选碳足迹。

前景数据来自 lca/dataset.yaml（cheme 导出的 1 h 未分配 LCI）；
背景采用公开的 DESNZ 2026 因子（OGL-3.0）：
  - 天然气上游（WTT）0.03021 kWh CO2e / kWh 燃料，LHV 13.1 kWh/kg
  - 英国电网 0.18436 kg CO2e / kWh
直接排放（工艺 CO2 + 烟道 CO2）按 cheme 的 elementary 流计。
去离子水缺少公开因子，保留为 gap，不按 0 处理。
"""
from __future__ import annotations

import json
from pathlib import Path

import bw2calc
import bw2data as bd
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "bed" / "lca"
PROJECT = "nsc-ammonia-bed"

NG_SUPPLY_KG_CO2E_PER_KG = 0.03021 * 13.1   # DESNZ WTT 天然气，LHV 13.1 kWh/kg
ELEC_KG_CO2E_PER_KWH = 0.18436              # DESNZ 2026 英国电网
GWP = {"co2": 1.0, "ch4": 29.8, "n2o": 273.0}


def amount(dataset, key):
    for ex in dataset.get("exchanges", []):
        if ex.get("key") == key:
            return float(ex.get("amount", 0.0))
    return 0.0


def main() -> int:
    dataset = yaml.safe_load((ROOT / "lca" / "dataset.yaml").read_text(encoding="utf-8"))
    nh3 = amount(dataset, "product:NH3") or 1.0
    ng = amount(dataset, "feed:NG") / nh3
    power = amount(dataset, "feed:POWER") / nh3
    co2 = amount(dataset, "emission:CO2") / nh3
    ch4 = amount(dataset, "emission:CH4") / nh3
    water = amount(dataset, "feed:DMW") / nh3

    if PROJECT in bd.projects:
        bd.projects.delete_project(PROJECT, delete_dir=True)
    bd.projects.set_current(PROJECT)
    for name in ("biosphere3", "ammonia-bed"):
        if name in bd.databases:
            del bd.databases[name]

    bio = bd.Database("biosphere3")
    bio.write(
        {
            ("biosphere3", "co2-fossil"): {
                "name": "carbon dioxide, fossil",
                "unit": "kg",
                "categories": ("air",),
                "type": "emission",
            },
            ("biosphere3", "ch4-fossil"): {
                "name": "methane, fossil",
                "unit": "kg",
                "categories": ("air",),
                "type": "emission",
            },
        }
    )
    method = bd.Method(("IPCC 2021", "GWP100"))
    method.write(
        [
            (("biosphere3", "co2-fossil"), GWP["co2"]),
            (("biosphere3", "ch4-fossil"), GWP["ch4"]),
        ]
    )

    fg = bd.Database("ammonia-bed")
    fg.write(
        {
            ("ammonia-bed", "natural-gas-supply"): {
                "name": "natural gas, supply (WTT), GB",
                "unit": "kg",
                "location": "GB",
                "exchanges": [
                    {
                        "amount": NG_SUPPLY_KG_CO2E_PER_KG,
                        "input": ("biosphere3", "co2-fossil"),
                        "type": "biosphere",
                    }
                ],
            },
            ("ammonia-bed", "electricity-gb"): {
                "name": "electricity, GB grid",
                "unit": "kWh",
                "location": "GB",
                "exchanges": [
                    {
                        "amount": ELEC_KG_CO2E_PER_KWH,
                        "input": ("biosphere3", "co2-fossil"),
                        "type": "biosphere",
                    }
                ],
            },
            ("ammonia-bed", "ammonia"): {
                "name": "ammonia, liquid, at battery limit",
                "unit": "kg",
                "location": "NL",
                "exchanges": [
                    {"amount": 1.0, "input": ("ammonia-bed", "ammonia"), "type": "production"},
                    {"amount": ng, "input": ("ammonia-bed", "natural-gas-supply"), "type": "technosphere"},
                    {"amount": power, "input": ("ammonia-bed", "electricity-gb"), "type": "technosphere"},
                    {"amount": co2, "input": ("biosphere3", "co2-fossil"), "type": "biosphere"},
                    {"amount": ch4, "input": ("biosphere3", "ch4-fossil"), "type": "biosphere"},
                ],
            },
        }
    )

    def score(code):
        lca = bw2calc.LCA({(("ammonia-bed", code)): 1.0}, ("IPCC 2021", "GWP100"))
        lca.lci()
        lca.lcia()
        return lca.score

    total = score("ammonia")
    ng_score = score("natural-gas-supply") * ng
    power_score = score("electricity-gb") * power
    direct = co2 * GWP["co2"] + ch4 * GWP["ch4"]

    OUT.mkdir(parents=True, exist_ok=True)
    result = {
        "functional_unit": "1 kg NH3 (liquid, battery limit)",
        "method": "IPCC 2021 GWP100 (CO2=1, CH4=29.8)",
        "total_kg_co2e": total,
        "direct_kg_co2e": direct,
        "natural_gas_supply_kg_co2e": ng_score,
        "electricity_kg_co2e": power_score,
        "gaps": ["demineralised water supply/treatment (no open factor in this run)"],
        "inputs": {"ng_kg": ng, "power_kwh": power, "dmw_kg": water},
        "status": "BED screening only, not a verified LCA",
    }
    (OUT / "brightway-result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = [
        "# 碳排筛选（Brightway 2.5）",
        "",
        "功能单位：1 kg 液氨（界区出口）。方法：IPCC 2021 GWP100。",
        "",
        "| 项目 | kg CO2e / kg NH3 | 说明 |",
        "|---|---:|---|",
        f"| 直接排放（工艺 CO2 + 烟道 CO2） | {direct:.4f} | cheme elementary 流 |",
        f"| 天然气上游（WTT） | {ng_score:.4f} | DESNZ 2026，0.03021 kWh/kWh × 13.1 kWh/kg |",
        f"| 外购电力 | {power_score:.4f} | DESNZ 2026 英国电网 0.18436 kg/kWh |",
        f"| **合计** | **{total:.4f}** | 筛选值 |",
        "",
        "缺口：去离子水制水与废水处理未计入（保留为 gap，不按 0 处理）；"
        "工艺 CO2 按全部排空计，未考虑 CCS/尿素联产；天然气组成与装置效率为概念级假设。",
        "",
        "结论：BED 方案级筛选值，可用于方案比较与排放热点识别，不可用于碳交易、许可或设计保证。",
    ]
    (OUT / "brightway-result.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
