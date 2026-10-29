# Resume bullets

Every claim below is true of this project. Do not add numbers you cannot defend.

## Short list (pick 3-4)

* Built a Python 3 command-line **EDA workflow automation simulator** (standard library only) that runs a six-stage flow (input validation, design preparation, elaboration, lint, simulation, timing) and returns CI-friendly exit codes.
* Implemented **configuration validation** (typed dataclasses, unknown-key and range checks) and **input-file validation** (extension, size, encoding, binary detection) with clear error messages.
* Designed **failure simulation** (error, timeout, crash) with **retry logic for transient faults**, so error handling and recovery paths can be tested on purpose.
* Added **timestamped logging** and **atomic JSON reports** (temp file + `os.replace`) capturing per-stage status, attempts, duration and metrics for every run.
* Wrote **96 `unittest` tests** covering config, validators, each stage, pipeline retry behaviour, reports, logging and the CLI; used injected clock/sleep for fast, deterministic tests.
* Made results **reproducible** with seeded, content-derived pseudo-random metrics, and documented the project with a Mermaid architecture diagram, troubleshooting guide and README.

## One-line project entry

**EDA Workflow Automation Simulator** - Python, argparse, unittest, JSON, logging - educational simulation of a chip-design verification flow with validation, retries, failure injection and reporting.

## 60-second pitch

"I built a small Python tool that simulates how a chip-design verification flow is automated. It takes a Verilog-style file, validates the input and the configuration, then runs six stages in order: preparation, elaboration, lint, a simulated test run and a timing check. Each stage records timestamps, status and metrics into a JSON report and a log. I added failure injection so I can prove the tool handles errors: normal failures stop the run, timeouts are retried, and unexpected crashes are caught and reported. It is an educational simulation, not a real EDA tool, but it taught me to design for reliability, reproducibility and testing, and it has 96 unit tests."
