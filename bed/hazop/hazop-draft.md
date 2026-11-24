# HAZOP 初稿（BED 方案级）

来源：`safety\hazop\H-01\study.yaml`（Rundown and LNG storage tanks），3 个节点、26 个偏差场景。

**状态：draft（草案），未经 HAZOP 团队评审，不得作为安全决策依据。**

## 初始风险分布

| 风险等级 | 场景数 |
|---|---:|
| high | 12 |
| low | 5 |
| medium | 8 |
| 未评级 | 1 |

## 工作表（前 40 行，完整见 hazop-worksheet.csv）

| 节点 | 参数 | 引导词 | 原因 | 后果 | 初始风险 | 剩余风险 |
|---|---|---|---|---|---|---|
| N1 | flow | no | XV-1102 closes (I-201 on T-2101 LAHH or I-203 on PAHH) while XV-1103 is already closed (I-301/I-303 on T-3101, T-3101 isolated for maintenance or in Phase 1, or | The rundown of up to four trains is deadheaded against closed valves: the header rises to the shut-off head of the trains' rundown pumps (not in the files, D-023 (3)); a closure of a DN 900 ESD valve  | high | medium |
| N1 | pressure | more | LNG blocked in LNG-1001 between XV-1111..XV-1114 (or the check valves CV1111..CV1114) and XV-1102/XV-1103 after I-101 or I-102 (since f5d925f6 also after the in | Thermal expansion overpressures the blocked-in rundown header. | high |  |
| N1 | pressure | more | LNG blocked in the fill branches between the ESD valve and the fill selection valves: LNG-1002/LNG-1004 between XV-1102 and XV-1106/XV-1107 when both selection  | Thermal expansion of trapped LNG overpressures the DN 900 fill lines; flange or valve body leak on the tank roof, LNG release at height. | high | medium |
| N1 | temperature | more | Train upset (end-flash or main cryogenic heat exchanger, outside the battery limit) sends warmer, less subcooled LNG; the subcooling of ~1.3 K (D-005) is lost. | The rundown flashes in the fill line (two-phase flow, vibration of LNG-1002/LNG-1004) and adds flash vapour to the tank; tank pressure rises (see N3-HP). | low |  |
| N1 | flow | reverse | One train trips and its rundown pressure at the battery limit falls below the header pressure while the other trains continue. | LNG flows back from the header into the tripped train's rundown line. | low |  |
| N1 | flow (spurious trip of the rundown) | no | Spurious I-102: ZSC-1102 or ZSC-1103 shows a valve closed that is open (switch or wiring fault, valve stem not made up), while the other fill ESD valve is close | I-102 closes XV-1111..XV-1114 at the full rundown rate and trips the four trains (since f5d925f6 through XS-1100 as the closure starts): loss of production for the whole plant, a pressure surge in LNG | medium |  |
| N1 | flow (spurious trip of the rundown) | no | Spurious I-102 on PZT-1105 (added in fac0bbb5): the single transmitter on LNG-1001 reads high-high (transmitter or impulse line fault, a frozen tapping, a calib | As S18: I-102 closes XV-1111..XV-1114 at the full rundown rate and trips all four trains (since f5d925f6 through XS-1100 as the closure starts), in both tank line-ups (the PZT-1105 path of I-102 does  | medium |  |
| N1 | flow (spurious trip of the rundown) | no | The instrument-air trip I-804 (PZT-8123A/B/C on IA-8001, P-08, 2oo3 at 4.5 barg, ASSUMED; added in f5d925f6) initiates I-102: on a real loss of instrument-air p | I-102 trips the four trains through XS-1100 and closes XV-1111..XV-1114 at the full rundown rate (closure at least 30 s): loss of production for the whole plant whatever the cause, together with ESD-1 | medium |  |
| N1 | pressure (surge on an air-failure closure) | more | Loss of instrument air while the non-return valve or the local air accumulator on the actuator supply of one of XV-1102, XV-1103, XV-1111..XV-1114 has failed un | A DN 900 rundown valve closes in a few seconds against the full rundown at 3.4 m/s, before or as XS-1100 trips the trains: surge of up to about +1,750 kPa for an instant closure (D-023 (3)) in LNG-100 | high |  |
| N1 | flow (fill selection permissive I-103) | no | A fill change (SEQ-FILL-CHANGE) in which the new selection valve is commanded open from its HS but does not open (actuator or solenoid fault, valve stuck closed | The old selection valve closes the last open fill branch of the only lined-up tank in at least 30 s against the full rundown: the header pressure rises, PZT-1105 trips I-102 (trains tripped through XS | medium |  |
| N2 | level | more | The rundown continues into T-2101 (T-3101) past its high level: LT-2101 reads low (radar fault) or the operator does not switch the fill to the other tank in ho | Overfill: LNG over the suspended deck into the roof space and the vapour outlet BOG-1001 (liquid to D-7101 and the compressors, H-04) and to the inlets of PSV-2131A/B, which would discharge LNG from e | high | high |
| N2 | level | more | I-201 (I-301) on LAHH or I-203 (I-303) on PAHH closes XV-1102 (XV-1103) while the whole rundown goes into that tank: since f5d925f6 the closure takes at least 3 | Up to about 63 m3 (7,560 m3/h for 30 s, less as the valve throttles) enters the tank after the high-high level trip point of LZT-2102 / LZT-2106; if the margin between the trip point and the overfill  |  |  |
| N2 | level | more | In holding, I-201 (I-301) trips on a high-high level of the tank that receives the circulation return, and XV-2123 (XV-3123) fails to close (actuator or solenoi | The circulation pump P-2102 (P-3102) keeps returning ~314 m3/h (rated 500 m3/h, D-008) through LNG-4005 into the tank past its high-high level (up to aedd8dbd, during a post-loading drain the jetty dr | high | medium |
| N2 | level | more | SEQ-LINE-EMPTY (added in c257902c, D-036 item 5 (b), 11 (b): a leak on the trestle side of a shore ESD valve after ESD-1) returns the leaking loading line, ~1,0 | I-201 (I-301) closes XV-2123 (XV-3123) and the fill, which also ends the displacement (the SEQ-LINE-EMPTY abort): the leaking line is left part-full with the N2 pushing against a closed return (H-02 S | medium |  |
| N2 | level | less | Withdrawal by the loading pumps (up to 12,000 m3/h from one tank, D-011) continues below the minimum submergence: LT-2101 reads high, or the loading is not swit | Submerged-motor pumps P-2101A..D and P-2102 cavitate and run dry; motor and bearing damage; loading stops. | medium |  |
| N2 | composition (density) | other-than | Stratification: the rundown differs in density from the tank heel (train off-spec or a different train mix, a weathered N2-depleted heel, D-009) and is filled a | Rollover: the layers mix suddenly and release BOG at many times the normal rate, beyond the BOG compressors and PV-1110; the tank pressure reaches PSV-2131A/B, which vent cold methane-rich vapour to a | high |  |
| N2 | temperature (annular space) | more | Inner-tank leak through the 9 % Ni inner tank into the annular space. | LNG in the annular space against the concrete outer tank (full containment holds it by design); cold spot, thermal stress of the outer tank and liner; boil-off increase. | low |  |
| N2 | temperature (tank base) | less | Failure of the tank bottom heating (controlled from TI-2105, not drawn on P-02). | Freezing of the ground below the base slab, frost heave and damage to the foundation. | medium |  |
| N3 | pressure | more | All running BOG compressors trip (I-701 on D-7101 LAHH, power failure, I-702 / I-702B / I-702C, I-703A..C; since f5d925f6 the control philosophy F-AIR also stat | Header and tank pressure rise; if PV-1110 does not take the BOG to the flare, the tanks reach +29 kPa(g) and PSV-2131A/B/C (PSV-3131A/B/C) vent cold BOG to atmosphere from the tank tops; above the rel | high | high |
| N3 | pressure | more | PV-1110 fails closed (loss of instrument air - its fail position in control/loops.yaml - or a stuck valve) while the BOG exceeds the running compressors' capaci | As S11; without another outlet the tank PSVs are the only remaining outlet. | high | high |
| N3 | pressure | more | Fire on the tank roof or at the tank (pool fire in the tank area, jet fire at a roof nozzle). | Heat input raises the boil-off beyond the BOG system; PSV-2131A/B relieve; fire escalation to the roof platform and pump columns. | high |  |
| N3 | pressure | more | Rapid fall of the barometric pressure (storm front at Kitimat) at constant tank absolute pressure demand. | Gauge pressure and boil-off rise; more BOG to the compressors and the flare. | low |  |
| N3 | pressure (vacuum) | less | Rapid withdrawal at the full loading rate from one tank (four pumps, 12,000 m3/h) with a low vapour return (carrier return-gas compressor not yet ramped up, S-0 | The vapour space pressure falls below the make-up range; at -0.3 kPa(g) PSV-2133A/B/C admit air into a tank full of methane: a flammable mixture in the vapour space and the BOG header; at a deeper vac | high | medium |
| N3 | pressure (vacuum) | less | Rapid rise of the barometric pressure (passing a low). | Gauge pressure falls toward the vacuum set point; as S15. | low |  |
| N3 | pressure (vacuum) | less | Subcooled rundown top-filled through the spray (XV-1106) at the full rundown rate into a tank with low boil-off: the spray condenses the vapour (D-005 notes the | Vapour space pressure falls toward vacuum; as S15. I-204 does not stop or switch the fill. | medium |  |
| N3 | relief capacity (inlet isolation) | less | A relief or vacuum valve inlet isolation left closed or part closed: HV-2134A/B/C (HV-3134A/B/C) under PSV-2131A/B/C (PSV-3131A/B/C) or HV-2135A/B/C (HV-3135A/B | Fewer than the N relief or vacuum valves the relief case needs (N+1 installed): on the next demand (loss of the BOG compressors at loading, fire, rollover, the fuel gas blow-by of D-026 item 8, since  | high |  |

## 使用边界

- 本初稿由 AI 辅助生成并经 cheme validate 校验，未召开正式 HAZOP 会议。
- 风险矩阵来自 `safety/risk-matrix.yaml`；SIL 定级、LOPA、定量风险分析均未开展。
- 详细设计阶段必须由多专业团队逐节点复核，并关闭 `cheme safety hazop check` 的未决项。