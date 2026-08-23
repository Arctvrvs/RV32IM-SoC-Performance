# Milestone 4A - Dhrystone full-workload correlation

This milestone moves from directed microarchitecture tests to the original RV32IM project's full Dhrystone image.

Configuration mirrors the original cached benchmark:

- 5-stage RV32IM pipeline
- 64-line, one-word direct-mapped I-cache
- 64-line, one-word direct-mapped write-back D-cache
- independent AXI-Lite I/D backing memories
- AXI memory `LATENCY=3`
- expected success signature `x5 = 0x003fffff`

The `published_rtl_baseline.csv` file records the historical result already present in the original RTL project's README. It is a reference only. The Milestone 4 VCS bundle performs a fresh simulation and produces a retirement trace, cache counters, and RTL event counters.

Before freezing the Milestone 4 model prediction, the analytical load-use rule was aligned with an explicit RTL optimization: store `rs2` data is consumed in MEM and can be forwarded from an older load, so `lw xN,...; sw xN,...` does not take a decode load-use bubble. This is an RTL-source-derived rule, not a fit to Dhrystone cycles.

Run on Windows:

```bash
python scripts/run_milestone4.py --model-only
```

Then run the VCS bundle on Linux, extract its result ZIP here, and run:

```bash
python scripts/run_milestone4.py --require-rtl
python scripts/analyze_milestone4_gaps.py
```
