# German Listening Tools

Shared pipeline scaffold for classic + marker processing and HITL label workflow.

## Commands

```powershell
# run all tests
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Tools\src'; .\.venv\Scripts\python.exe -m pytest Tools\tests -q

# marker full flow
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Tools\src'; .\.venv\Scripts\python.exe -m glist_pipeline.cli run-all --mode marker

# marker live run via LangGraph
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Tools\src'; .\.venv\Scripts\python.exe -m glist_pipeline.cli live-run --mode marker

# app menu (3-action flow)
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Tools\src'; .\.venv\Scripts\python.exe -m glist_pipeline.cli

# HITL label decision
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Tools\src'; .\.venv\Scripts\python.exe -m glist_pipeline.cli labels --action accept --block-id teil-1
```

## EXE Packaging (Secondary Deliverable)

```powershell
# install packager
.\.venv\Scripts\python.exe -m pip install pyinstaller

# build one-file executable for app entry
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Tools\src'; \
.\.venv\Scripts\pyinstaller.exe --onefile --name GermanListeningCLI \
C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Tools\src\glist_pipeline\cli.py

# output binary path
# .\dist\GermanListeningCLI.exe
```

Notes:
- EXE is packaging layer only; product behavior remains defined by app flow contract.
- Marker MVP verification should be completed before relying on packaged binary.
