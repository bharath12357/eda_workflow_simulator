# Troubleshooting (Windows 11 + VS Code)

| Symptom | Cause | Fix |
|---|---|---|
| `'py' is not recognized` | Python not installed or launcher missing | `winget install --id Python.Python.3.12 -e`, reopen the terminal |
| `'python' is not recognized` / opens Microsoft Store | PATH not set / Store alias | Use `py -3` instead, or reinstall Python with "Add python.exe to PATH" |
| `No module named eda_sim` | You are not in the project root | `cd` to the folder that contains the `eda_sim` folder, then rerun |
| `ImportError: attempted relative import` / `No module named tests` | Tests run from the wrong folder or without `-t .` | From the project root: `py -3 -m unittest discover -s tests -t . -v` |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` or use `activate.bat` in Command Prompt |
| `ERROR: Config file not found` | Wrong relative path | Run from the project root; use backslashes on Windows: `config\default_config.json` |
| `ERROR: Unknown key(s) in 'lint'` | Typo in config | Compare with `config\default_config.json` |
| `ERROR: ... 'stages' must follow the order` | Stages listed out of order | Keep the order shown by `list-stages` |
| `FAILED ... Input file not found` | Wrong design path | Check the path; the failure is recorded in the report on purpose |
| Exit code 1 | The workflow failed (expected for the `broken_*` samples) | Read the table / JSON `error` field |
| Exit code 2 | Bad config, bad flags, unreadable report | Read the `ERROR:` line on stderr |
| VS Code does not find tests | Wrong interpreter or old cache | `Ctrl+Shift+P` -> *Python: Select Interpreter*, then *Test: Refresh Tests* |
| VS Code shows yellow import warnings | Interpreter not selected | Select the interpreter; the workspace setting adds the project root to the path |
| `PermissionError` writing reports/logs | Folder is read-only or synced/locked | Use `--report-dir` and `--log-dir` with a writable folder such as `%USERPROFILE%\eda_out` |
| Old log still open / cannot delete `logs\*.log` | A process still holds it | Close the terminal running the tool; the tool closes handlers when it finishes |
| Strange characters in the console | Console code page | `chcp 65001` or use Windows Terminal; the tool prints only ASCII |
| `git push` rejected / asks for a password | GitHub no longer accepts passwords | Sign in through the browser prompt from Git Credential Manager, or use a personal access token |

## Debugging tips

1. Re-run with `--log-level DEBUG` and read the file in `logs\`.
2. Open the JSON report: every stage has `status`, `attempts`, `error`, `metrics`.
3. Reproduce one stage in isolation by calling it in a test (see `tests\test_stages.py`).
4. Use VS Code breakpoints (`F5`) in `eda_sim\pipeline.py`, `_run_stage`.
5. If a stage reports "must run first", check that `stages` in your config still contains the earlier stage.
