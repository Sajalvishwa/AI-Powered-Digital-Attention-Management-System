# desktop-agent

Headless background tracker for Windows (Phase 3 in docs/tasks.md).

## Run (PowerShell, from this folder)
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pytest -q
python -m app.main --debug      # Ctrl+C to stop
```
First run creates `%APPDATA%\AttentionAgent\config.toml` and `agent.log`.
Use `--data-dir somefolder` to keep everything elsewhere while developing.
