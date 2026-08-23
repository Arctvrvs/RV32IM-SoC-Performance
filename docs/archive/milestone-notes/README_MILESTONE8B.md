# Milestone 8B — SAIF-Driven Genus Power + Dhrystone Energy

## Goal
Use the validated Milestone 8A Dhrystone SAIF activity to estimate **same-flow standard-cell power** for the three M7B architecture points, then convert average power into workload energy.

Architectures:
- BASE_64_64 — 1,365,926 cycles, 6.71875 ns
- EFF_256_64 — 715,815 cycles, 6.87500 ns
- PERF_512_64 — 373,403 cycles, 6.71875 ns

## Method
1. Read RTL and elaborate `rv32im_soc_synth_cfg`.
2. Rename only the SAIF root from `tb_m8a_dhrystone` to `rv32im_soc_synth_cfg`; `cpu`, `icache`, and `dcache` remain unchanged.
3. Read SAIF **after elaboration and before mapping**.
4. Synthesize once at each architecture's M7B tightest-MET slow-corner period.
5. Run `report_power` after mapping/optimization.
6. Compute benchmark energy:

`energy_nJ = average_power_mW × runtime_us`

## Important interpretation boundary
The I$ and D$ arrays remain RTL register arrays mapped into standard cells. These results are useful for **relative same-flow architecture comparison**, but they are **not SRAM-macro power** and not post-route silicon power.

## Expected directory relationship
Unzip `m8b_power` beside the populated M8A folder:

```
RV32IM/
  m8a_activity/
    results/milestone8a/slow/.../dhrystone_activity.saif
  m8b_power/
```

If M8A is elsewhere, pass `--activity-root PATH`.

## Commands

```bash
cd m8b_power
python3 scripts/preflight_genus_power.py
python3 scripts/run_genus_power.py --corner slow
python3 scripts/analyze_power.py --corner slow
python3 scripts/package_power_results.py
```

First-case-only test:

```bash
python3 scripts/run_genus_power.py --corner slow --case BASE_64_64
python3 scripts/analyze_power.py --corner slow
```

Force regeneration:

```bash
python3 scripts/run_genus_power.py --corner slow --force
```
