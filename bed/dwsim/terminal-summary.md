# LNG export marine terminal (2 x 225,000 m3, 2 berths, 28 MTPA) — Terminal Summary

**Plant**: LNG export marine terminal (2 x 225,000 m3, 2 berths, 28 MTPA)
**Capacity**: 28 MTPA
**Cases (flowsheet)**: average, loading, holding
**Stage**: concept

## 设计输入边界
- Feeds: RUNDOWN, SHIPVAP, INVDRAW, POWER
- Products: SHIP, BOGOUT, INVFILL
- **物料包**: GERG-2008 (CoolProp reference EOS), 非 Aspen/Peng-Robinson
- **无 DWSIM simulation.yaml**；流股由 scripts/terminal_sizing.py 生成
- **单位**: kPa(a) / K / kg/h

## 主要设备
| 类型 | 数量 | 代表标签 |
|---|---:|---|
| LNG 储罐 (225,000 m³) | 4 | T-2101, T-3101, T-8101, T-8102 |
| 泵 (含内泵) | 16 | P-2101A ... |
| BOG 压缩机 | 3 | K-7101A ... |
| **合计** | **36** | — |

## 管线分布 (by fluid)
| 流体 | 条数 |
|---|---:|
| LNG | 78 |
| Boil-off gas | 46 |
| Nitrogen | 8 |
| Flare gas | 7 |
| Air | 6 |
| Fuel gas | 3 |
| Rainwater | 2 |
| Instrument air | 1 |

## 管线口径分布
| DN | 条数 |
|---|---:|
| DN100 | 9 |
| DN150 | 13 |
| DN200 | 1 |
| DN25 | 36 |
| DN250 | 19 |
| DN300 | 5 |
| DN400 | 16 |
| DN450 | 6 |
| DN50 | 9 |
| DN500 | 6 |
| DN600 | 2 |
| DN750 | 4 |
| DN80 | 11 |
| DN800 | 8 |
| DN900 | 6 |

## 关键流股 (case: average)
| Stream | 描述 | P kPa(a) | T K | Flow kg/h | Composition |
|---|---|---:|---:|---:|---|
| S1 | LNG rundown from the liquefaction trains | ? | ? | ? |  |
| S13 | Tank liquid to the in-tank pumps | ? | ? | ? |  |
| S2 | Pumped LNG to the trestle loading lines | ? | ? | ? |  |
| S7 | LNG spray to the BOG desuperheater | ? | ? | ? |  |
| S3 | LNG at the jetty (loading berth) | ? | ? | ? |  |
| S10 | Circulation return to the tanks (holding) | ? | ? | ? |  |
| S4 | LNG to the carrier | ? | ? | ? |  |
| S5 | Carrier return vapour, BOG design envelope | ? | ? | ? |  |
| S6 | Vapour return over the trestle | ? | ? | ? |  |
| S8 | Tank boil-off and displaced vapour | ? | ? | ? |  |
| S14 | BOG after the desuperheater to the compressor | ? | ? | ? |  |
| S9 | Compressed BOG to the trains | ? | ? | ? |  |
| S11 | Tank inventory drawn down (loading) | ? | ? | ? |  |
| S12 | Tank inventory filled up (holding) | ? | ? | ? |  |
| E1 | In-tank pump motors (electric) | ? | ? | ? |  |
| E2 | BOG compressor motors (electric) | ? | ? | ? |  |

> 备注：所有 state 来自 `flowsheet.yaml` 的 provenance `scripts/terminal_sizing.py`，source=GERG-2008 (CoolProp)。P&ID 见 bed/pid/*.svg，三维见 bed/cad/ammonia-bed.step。