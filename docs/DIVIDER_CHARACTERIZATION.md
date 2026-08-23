# Milestone 2.6 - Divider Characterization

This suite measures divider timing without changing the timing model. All five
cases are intentionally `MEASURE` cases.

Cases:

- `divider_single`: isolates first-result latency.
- `divider_dependent`: places an ADD immediately after DIV that consumes its result.
- `divider_independent`: follows DIV with independent integer work.
- `divider_back_to_back`: issues DIV/DIVU/REM/REMU consecutively to measure throughput.
- `divider_idle_gap`: separates two DIV instructions with eight independent instructions to determine whether startup latency is paid again after the divider drains.

Windows, before VCS:

```
python scripts/run_divider_characterization.py --model-only
```

After extracting the VCS results ZIP at this project root:

```
python scripts/run_divider_characterization.py --require-rtl
```

Do not modify divider timing parameters until the RTL traces have been analyzed.
