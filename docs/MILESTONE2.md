# Milestone 2A — Analytical 5-stage pipeline timing

This milestone turns the Milestone 1 functional/reference model into the first useful performance-correlation model.

## Calibrated RTL behavior

The VCS smoke trace retires 10 instructions at cycles:

```text
5, 6, 7, 8, 9, 10, 11, 13, 16, 17
```

The timing model derives the same sequence from the program itself:

- 10 retired instructions
- 4 cycles of 5-stage pipeline fill/drain
- 1 load-use stall (`LW x5` immediately followed by `BEQ` consuming `x5`)
- 2 cycles of taken-branch redirect/flush penalty

Therefore:

```text
10 + 4 + 1 + 2 = 17 predicted cycles
CPI = 17 / 10 = 1.7000
```

The RTL trace is **not** used to generate this prediction. It is read only after the model executes to calculate correlation error.

## Current calibrated rules

`PipelineTimingModel` currently implements only behavior supported by the first RTL measurement:

1. Five-stage pipeline: ideal completion is `N + 4` cycles.
2. Immediate load-use dependency: +1 cycle.
3. Taken conditional branch: +2 cycles applied to following retirement(s).
4. MUL: no extra penalty observed in the smoke workload.
5. DIV/REM: intentionally uncalibrated; divider penalty remains zero until a directed VCS workload is measured.
6. I-cache, D-cache, and AXI stalls: deferred to Milestone 3.

## Run on Windows

With `results/rtl_trace.csv` already copied back from the Linux/VCS VM:

```bash
python scripts/run_milestone2.py
```

Or manually:

```bash
cmake -S . -B build -DRV32IM_BUILD_SYSTEMC=OFF
cmake --build build --config Release

./build/Release/rv32im_model.exe \
    workloads/smoke.hex \
    --trace results/model_trace.csv \
    --rtl-trace results/rtl_trace.csv \
    --dump-regs

python scripts/compare_traces.py \
    results/model_trace.csv \
    results/rtl_trace.csv \
    --compare-cycle
```

Expected correlation:

```text
model cycles            : 17
RTL cycles              : 17
model CPI               : 1.7000
RTL CPI                 : 1.7000
cycle error             : 0.00%
result                  : PASS (exact cycle correlation)
```

## Next validation step

- no-hazard baseline
- multiple load-use dependencies
- taken and not-taken branches
- DIV/REM dependency/throughput cases

