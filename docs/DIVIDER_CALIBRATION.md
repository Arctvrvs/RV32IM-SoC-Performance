# Divider Timing Calibration

## Measured RTL behavior

Directed VCS characterization established the timing of `DIV`, `DIVU`, `REM`, and `REMU` in the current RV32IM RTL:

- divider pipeline latency: **8 cycles**
- initiation interval: **1 cycle**
- first divider operation in a contiguous burst adds **7 stall cycles** relative to the ideal five-stage pipeline
- immediately consecutive divider operations retire one per cycle after the first result
- dependent and independent instructions behind the first divider are both held behind the divider result stream in this in-order implementation
- any intervening non-divider instruction ends the contiguous divider burst; a later divider operation pays the seven-cycle startup again

## Calibrated directed results

| Test | Calibrated model cycles | RTL cycles | Expected error |
|---|---:|---:|---:|
| divider_single | 15 | 15 | 0.00% |
| divider_dependent | 16 | 16 | 0.00% |
| divider_independent | 17 | 17 | 0.00% |
| divider_back_to_back | 18 | 18 | 0.00% |
| divider_idle_gap | 31 | 31 | 0.00% |
| validation/divider | 20 | 20 | 0.00% |

## Analytical rule

The timing model charges `divider_latency - 1` before the retirement of the first DIV/REM operation in each contiguous divider burst. With the measured configuration:

```text
divider_latency             = 8
divider_initiation_interval = 1
startup penalty             = 8 - 1 = 7 cycles
```

If the immediately previous architecturally executed instruction is also a DIV/DIVU/REM/REMU, no new startup penalty is charged because the RTL divider accepts one operation per cycle. A non-divider instruction ends that burst.

The RTL trace remains a post-prediction correlation source only; it is not consulted by `PipelineTimingModel` while calculating cycles.
