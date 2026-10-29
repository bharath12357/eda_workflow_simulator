# Upload to GitHub (free)

## One-time
1. Create a free account at <https://github.com>.
2. Install Git: `winget install --id Git.Git -e`, then reopen PowerShell.
3. Tell Git who you are:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## Create the repository on GitHub
1. GitHub -> **New repository**.
2. Name: `eda-workflow-automation-simulator`. Keep it **Public** (recruiters can see it). Do **not** tick "Add a README" (you already have one).
3. Click **Create repository** and copy the HTTPS URL, e.g. `https://github.com/YOUR-USER/eda-workflow-automation-simulator.git`.

## Push your project

```powershell
cd C:\path\to\eda_workflow_simulator
git init -b main
git add .
git status                      # check: no .venv, no __pycache__, no reports/logs json/log
git commit -m "Initial commit: EDA workflow automation simulator"
git remote add origin https://github.com/YOUR-USER/eda-workflow-automation-simulator.git
git push -u origin main
```

A browser window asks you to sign in the first time (Git Credential Manager). The `.gitignore` already excludes `.venv/`, `__pycache__/`, generated reports and logs.

## Later changes

```powershell
git add .
git commit -m "Describe what you changed"
git push
```

## Make the repo look professional
* Add a description and topics (`python`, `automation`, `eda`, `unittest`) with the gear icon next to **About**.
* The Mermaid diagram in `README.md` renders automatically on GitHub.
* Optional: add a GitHub Actions workflow `.github/workflows/tests.yml`:

```yaml
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m unittest discover -s tests -t . -v
```

## No Git? Use the website
Repository page -> **Add file** -> **Upload files** -> drag the project folder contents (not the zip) -> **Commit changes**.
