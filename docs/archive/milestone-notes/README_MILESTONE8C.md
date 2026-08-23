# Milestone 8C — Consolidated Architecture Selection

## Goal
Combine the already validated M7B performance/area/Fmax results with M8B SAIF-driven Genus power/energy results and make the final architecture tradeoff explicit.

This milestone does **not** run VCS or Genus. It is a reproducible analysis/report step and should complete in seconds.

## Inputs
Preferred live inputs are sibling results:

```text
../m7b_fmax/results/milestone7b/slow/best_points.csv
../m8b_power/results/milestone8b/slow/power_summary.csv
```

A locked `reference/validated_reference.csv` is bundled as a fallback using the already PASSed M7B/M8B values. Use `--strict` if you want the script to refuse fallback data.

## Metrics
- wall-clock speedup
- area ratio
- power ratio
- energy ratio / energy reduction
- normalized performance / area
- normalized performance / watt
- normalized performance / (watt × area)
- EDP and normalized EDP efficiency
- ED²P and normalized ED²P efficiency
- four-objective Pareto label using runtime, area, total power, and workload energy

No arbitrary weighted PPA score is used.

## Run
Place this folder beside `m7b_fmax` and `m8b_power`:

```text
RV32IM/
  m7b_fmax/
  m8b_power/
  m8c_selection/
```

Then:

```bash
cd m8c_selection
python3 scripts/run_architecture_selection.py --corner slow --strict
```

If your sibling result folders are elsewhere:

```bash
python3 scripts/run_architecture_selection.py --corner slow --strict \
  --m7b-root /path/to/m7b_fmax \
  --m8b-root /path/to/m8b_power
```

Outputs:

```text
results/milestone8c/slow/architecture_selection.csv
results/milestone8c/slow/architecture_selection_report.txt
results/milestone8c/slow/architecture_selection_report.md
results/milestone8c/slow/charts/wall_speedup.svg
results/milestone8c/slow/charts/energy.svg
results/milestone8c/slow/charts/perf_per_area.svg
results/milestone8c/slow/charts/perf_per_watt.svg
```

Package after review:

```bash
python3 scripts/package_selection_results.py
```

## Interpretation boundary
- Fmax is a synthesis/pre-layout target boundary, not post-route/silicon Fmax.
- Cache arrays are RTL register arrays mapped into standard cells, not SRAM macros.
- Power is SAIF-driven same-flow Genus/Joules estimation, not post-layout signoff power.
- The final choice is Dhrystone-specific, not a universal cache optimum.
