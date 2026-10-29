# 20 Arm-focused interview questions with answers

Tip: always say up front that your project is an **educational simulation**, then connect it to real concepts. Answers are written to be spoken in 30-60 seconds. Verify any Arm product details on arm.com before an interview, because product names change.

## Part A - Your project

**1. Tell me about your project in one minute.**
It is a Python command-line tool that simulates an automated chip-design verification flow. It validates the input file and the config, runs six stages (input validation, design preparation, elaboration, lint, simulation, timing), logs with timestamps, and writes a JSON report. It can inject failures to test error handling and retry. It is an educational simulation, not a real EDA tool, and has 96 unit tests.

**2. Why did you build it?**
Hardware teams run big automated flows and regressions, and the engineers who build that glue are software engineers. I wanted to practise the engineering qualities that matter there: reliability, reproducibility, clear errors, logging and tests.

**3. Walk me through the architecture.**
`cli.py` parses arguments and loads/validates the config. `pipeline.py` runs stages from `stages.py` in order against a shared context. `failures.py` can inject faults. `logger_setup.py` writes console and file logs. `report.py` writes the JSON report atomically. Exit codes tell scripts what happened: 0 pass, 1 workflow failed, 2 usage/config error.

**4. How do you handle errors?**
I use a small exception hierarchy. Expected problems (`StageError`, `InputValidationError`, `ConfigError`) are caught, logged and recorded in the report. A transient `SimulatedTimeoutError` is retried up to `retry.max_attempts`. Anything else is caught by a last-resort `except Exception` that logs the traceback and marks the stage failed, so one bug never loses the report.

**5. Why retry only timeouts?**
Retrying makes sense for transient faults (a busy licence server, a flaky network disk). A deterministic failure like an unbalanced module will fail again, so retrying wastes time and hides the real problem.

**6. How did you test it, and what did testing teach you?**
`unittest` with 96 tests: config validation, each stage, retry, reports, logging and the CLI end to end. I inject the clock and sleep function so tests are fast and deterministic. Capturing sample output also exposed a real bug: two runs in the same second had the same run id and overwrote each other's report, so I added milliseconds to the id and a regression test.

**7. Why write the JSON report atomically?**
A crash or power loss during a normal write can leave a half-written file that breaks downstream tools. I write a temp file in the same folder and then `os.replace` it, which is atomic on both Windows and Linux for same-volume moves.

**8. How would you scale this to thousands of designs?**
Treat each design run as an independent job: a `regression` command that discovers files, runs jobs in parallel (`concurrent.futures` locally, or a scheduler such as Slurm or LSF on a farm), aggregates JSON reports into a pass-rate table, and keeps per-job logs. I would add timeouts, resource limits and a result database.

**9. How do you make results reproducible?**
Fixed seeds, deterministic inputs, versions recorded in the report, and the full config embedded in every report. My simulated metrics are derived from the seed plus a CRC of the file, so the same file and seed always give the same result.

## Part B - EDA / hardware flow concepts

**10. Describe a typical digital chip design flow.**
Specification, RTL design in Verilog/SystemVerilog/VHDL, lint and simulation-based verification, synthesis to gates, floorplan and place-and-route, static timing analysis, physical checks (DRC/LVS), power analysis and sign-off, then tape-out. Real verification is heavily automated and re-run constantly as the RTL changes.

**11. What is RTL?**
Register-Transfer Level: a description of hardware as registers and the logic between them, written in a hardware description language. My `counter.v` is a tiny RTL-style example.

**12. What are lint and elaboration?**
Lint finds risky or non-conforming code early (style and likely bugs). Elaboration builds the design hierarchy by resolving module instances and parameters; an undefined module fails here. My stages mimic these ideas with simple checks.

**13. What is static timing analysis and slack?**
STA checks that signals meet setup and hold requirements across all paths without simulating vectors. Slack = required time - arrival time; negative slack is a timing violation. My timing stage uses an invented path delay against the clock period to show the idea.

**14. Code coverage vs functional coverage?**
Code coverage measures which lines/branches/toggles the tests executed. Functional coverage measures whether the specified behaviours and scenarios were exercised. High code coverage does not prove the important scenarios were tested.

## Part C - Arm and architecture

**15. What does Arm do, at a high level?**
Arm designs processor architectures and CPU/GPU/system IP and licenses them to partners, who build chips. Because the IP goes into very many products, correctness, verification and quality automation matter a lot.

**16. RISC vs CISC, and where does Arm fit?**
RISC uses a smaller set of simpler, mostly fixed-length instructions and a load/store model (only load/store touch memory), which helps efficiency and pipelining. Arm is a RISC architecture; AArch64's A64 instruction set uses fixed 32-bit instructions.

**17. What are AArch64, Armv8-A and Armv9-A?**
AArch64 is the 64-bit execution state introduced with Armv8-A, alongside AArch32. Armv9-A builds on Armv8-A with additions such as SVE2 and enhanced security features. (Check Arm's documentation for the exact current list.)

**18. What is big.LITTLE (and DynamIQ)?**
A heterogeneous design that combines high-performance cores with energy-efficient cores so the OS can schedule work for the best performance-per-watt. DynamIQ is Arm's later, more flexible clustering approach for mixing core types.

**19. What are TrustZone and cache coherency, briefly?**
TrustZone is Arm's hardware-based security extension that separates a secure world from a normal world. Cache coherency keeps multiple cores' caches consistent, which Arm's AMBA protocols (for example ACE and CHI) support in multi-core systems.

**20. A nightly regression suddenly has 200 failures. How do you debug it?**
Check what changed (commits, tool versions, config, environment). Look for a common error signature in the logs, since 200 failures with one message usually means one cause. Reproduce one failure locally with the same seed and config. Bisect the commits. Distinguish real design bugs from infrastructure faults (timeouts, disk full), which is why my tool separates `StageError` from timeouts and unexpected crashes in the report. Fix, add a test or check so it cannot silently return, and report the root cause.

## Bonus quick answers

* **Why `pathlib`?** Object-based paths that handle Windows/Linux separators safely.
* **Why type hints and docstrings?** Readable contracts; editors and tools can catch mistakes.
* **Why only the standard library?** No install friction, nothing to audit, and it runs anywhere Python runs.
* **What would you improve next?** Parallel regression runner, HTML dashboard, CI on GitHub Actions, structured (JSON) logs.
