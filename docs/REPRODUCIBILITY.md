# Reproducibility Guide

## 1. Build the C++ model

The core model requires CMake 3.16 or newer and a C++17 compiler.

~~~bash
cmake -S . -B build -DRV32IM_BUILD_SYSTEMC=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
~~~

For an optional SystemC runner, set <code>SYSTEMC_HOME</code> and omit <code>-DRV32IM_BUILD_SYSTEMC=OFF</code>. CMake still builds the standalone model when SystemC is unavailable.

## 2. Run a directed workload

Single-configuration generators place the executable at <code>build/rv32im_model</code>. Multi-configuration Windows generators normally place it at <code>build/Release/rv32im_model.exe</code>.

~~~bash
./build/rv32im_model workloads/smoke.hex \
  --trace results/model_trace.csv \
  --dump-regs
~~~

Useful model options include:

~~~text
--enable-caches
--icache-lines <power-of-two>
--dcache-lines <power-of-two>
--memory-latency <cycles>
--dmem-hex <path>
--rtl-trace <path>
~~~

The complete option list is emitted by passing <code>--help</code> after a workload path.

## 3. Run model-only validation

~~~bash
python scripts/run_validation_suite.py --model-only
~~~

The directed suite covers ideal flow, load-use hazards, branches, and divider behavior. Workload images are under <code>workloads/validation/</code>.

## 4. Compare model and RTL traces

The RTL collector writes retirement events while suppressing held MEM/WB cycles marked as memory stalls. Compare a model trace against a collected RTL trace with:

~~~bash
python scripts/compare_traces.py \
  results/model_trace.csv \
  results/rtl_trace.csv
~~~

Aggregate correlation can also be printed by passing the RTL trace directly to the model:

~~~bash
./build/rv32im_model workloads/smoke.hex \
  --trace results/model_trace.csv \
  --rtl-trace results/rtl_trace.csv
~~~

## 5. Reproduce architecture-selection analysis

The consolidated selection script can use sibling M7B/M8B result trees or the locked values in <code>reference/validated_reference.csv</code>:

~~~bash
python scripts/run_architecture_selection.py
~~~

Use <code>--strict</code> when live M7B and M8B inputs are required and fallback reference data must be rejected.

## 6. External-flow boundary

Reproducing VCS simulation, Genus synthesis/power, or Innovus floorplanning requires the original CPU RTL, commercial EDA tools, and licensed technology collateral. Those inputs are not distributed in this repository.

The checked-in public evidence under <code>docs/results/</code> is a curated snapshot. The full local <code>results/</code> directory is intentionally ignored because it contains roughly 900 MB of generated traces, logs, reports, mapped netlists, and physical-design work files.