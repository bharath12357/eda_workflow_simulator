# Architecture

## Component diagram

```mermaid
flowchart LR
    U[User / VS Code terminal] --> CLI[cli.py<br/>argparse]
    CLI --> CFG[config.py<br/>load + validate]
    CFG -->|Config| PIPE[pipeline.py<br/>Pipeline.run]
    CLI -->|run id| LOG[logger_setup.py]
    PIPE --> INJ[failures.py<br/>FailureInjector]
    PIPE --> S1[1 input_validation]
    S1 --> S2[2 design_prep]
    S2 --> S3[3 elaboration]
    S3 --> S4[4 lint]
    S4 --> S5[5 simulation]
    S5 --> S6[6 timing]
    S1 -.uses.-> VAL[validators.py]
    PIPE --> LOG
    PIPE -->|WorkflowReport| REP[report.py<br/>atomic JSON write]
    REP --> OUT[(reports/*.json)]
    LOG --> LF[(logs/*.log)]
```

## Stage attempt flow (retry logic)

```mermaid
flowchart TD
    A[Start attempt n] --> B[optional simulated delay]
    B --> C{FailureInjector<br/>targets this stage?}
    C -->|timeout, n <= fail_attempts| T[SimulatedTimeoutError]
    C -->|error| E[StageError]
    C -->|crash| X[RuntimeError]
    C -->|no| R[stage.run]
    R -->|ok| P[PASSED]
    R -->|StageError| F[FAILED, no retry]
    T --> Q{n < max_attempts?}
    Q -->|yes| A
    Q -->|no| F2[FAILED after retries]
    E --> F
    X --> F3[FAILED, traceback logged]
```

## Data flow

1. `cli.py` parses arguments, loads the config (`config.py`), applies flag overrides and re-validates.
2. A **run id** (UTC time with milliseconds, e.g. `20261018T071851686Z`) names the log and report files so runs never overwrite each other.
3. `Pipeline.run` creates a `StageContext` (config, design path, shared `state` dict). Stages communicate only through `state` (e.g. `design_prep` stores `modules`, `elaboration` reads it). A stage that needs missing state fails with a clear "must run first" error.
4. Each stage returns `StageOutput(messages, metrics)` or raises. The pipeline turns that into a `StageResult` with start/end timestamps, duration and attempts.
5. The first non-passing stage stops the run; remaining stages are `SKIPPED`.
6. `report.write_report` writes JSON to a temp file in the same folder, then `os.replace` moves it into place (atomic).

## Design decisions

| Decision | Why |
|---|---|
| Custom exception hierarchy | Separates expected failures (`StageError`) from bugs (anything else) |
| Frozen dataclasses for config | Immutable, typed, validated once at the edge |
| Reject unknown config keys | A typo should be an error, not silently ignored |
| Injectable clock and sleep | Fast, deterministic tests with no real waiting |
| Seeded RNG from seed + file CRC | Reproducible "tool results" like a real regression |
| Atomic report writes | No half-written JSON if the process dies |
| Run id with milliseconds | Two runs in the same second must not collide (found and fixed while capturing sample output) |
| Exit codes 0/1/2 | CI systems and scripts can react to the result |
