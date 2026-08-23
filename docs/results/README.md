# Curated Results

This directory contains the compact, GitHub-facing evidence set. The full generated <code>results/</code> tree remains available locally but is ignored by Git.

## Final reports

- [Project overview](PROJECT_OVERVIEW.md)
- [Final technical report](FINAL_TECHNICAL_REPORT.md)
- [Verification and correlation](VERIFICATION_AND_CORRELATION.md)
- [Claims and limitations](CLAIMS_AND_LIMITATIONS.md)
- [Final architecture decision](FINAL_ARCHITECTURE_DECISION.txt)

## Machine-readable evidence

- [Canonical results](canonical_results.csv)
- [Milestone summary](MILESTONE_SUMMARY.csv)
- [Evidence manifest](EVIDENCE_MANIFEST.csv)

## Architecture and project flow

<p align="center">
  <a href="../assets/project_flow.svg"><img src="../assets/project_flow.svg" alt="Project flow" width="820"></a>
</p>

<p align="center">
  <a href="../assets/pipeline_architecture.svg"><img src="../assets/pipeline_architecture.svg" alt="RV32IM pipeline architecture" width="900"></a>
</p>

## Quantitative result gallery

| Cycle speedup | Physical core area | Performance per area |
|---|---|---|
| [![Cycle speedup](../assets/sram_normalized_cycle_speedup.svg)](../assets/sram_normalized_cycle_speedup.svg) | [![Core area](../assets/sram_normalized_core_area.svg)](../assets/sram_normalized_core_area.svg) | [![Performance per area](../assets/sram_normalized_perf_per_area.svg)](../assets/sram_normalized_perf_per_area.svg) |

<p align="center">
  <a href="../assets/sram_performance_vs_area.svg"><img src="../assets/sram_performance_vs_area.svg" alt="Cycle performance versus physical core area" width="700"></a>
</p>

## Genus schematic gallery

| Top-level SoC | Pipeline detail |
|---|---|
| [![Top-level schematic](../assets/genus_top_soc_schematic.gif)](../assets/genus_top_soc_schematic.gif) | [![Pipeline detail](../assets/genus_rv32im_pipeline_detail.gif)](../assets/genus_rv32im_pipeline_detail.gif) |
| Full pipeline | Banked SRAM wrapper |
| [![Full pipeline](../assets/genus_rv32im_pipeline_full.gif)](../assets/genus_rv32im_pipeline_full.gif) | [![Banked SRAM](../assets/genus_sram32_banked_schematic.gif)](../assets/genus_sram32_banked_schematic.gif) |

## CPU pipeline detail

The detailed CPU capture consolidates the mapped memory, control, writeback, and retirement-trace paths into a single full-resolution view.

<p align="center">
  <a href="../assets/cpu_pipeline_detailed.png"><img src="../assets/cpu_pipeline_detailed.png" alt="Detailed mapped RV32IM CPU pipeline" width="760"></a>
</p>

<p align="center">
  <a href="../assets/rtl_top_mapped_schematic.png"><img src="../assets/rtl_top_mapped_schematic.png" alt="Top mapped RTL schematic capture" width="600"></a>
</p>

## Physical floorplan gallery

| <code>BASE_64_64</code> | <code>EFF_256_64</code> | <code>PERF_512_64</code> |
|---|---|---|
| [![BASE floorplan](../assets/innovus_BASE_64_64_floorplan.png)](../assets/innovus_BASE_64_64_floorplan.png) | [![EFF floorplan](../assets/innovus_EFF_256_64_floorplan.png)](../assets/innovus_EFF_256_64_floorplan.png) | [![PERF floorplan](../assets/innovus_PERF_512_64_floorplan.png)](../assets/innovus_PERF_512_64_floorplan.png) |
| 4 SRAM macros, 0.4473 mm^2 | 6 SRAM macros, 0.6656 mm^2 | 10 SRAM macros, 1.0497 mm^2 |

## Selection summary

- <code>BASE_64_64</code>: minimum physical area.
- <code>EFF_256_64</code>: best equal-clock performance per physical core area.
- <code>PERF_512_64</code>: minimum Dhrystone cycle count.

No SRAM-aware Fmax or wall-clock claim is made because the physically matched SRAM timing library contains placeholder clock-to-Q values.