# Build the desktop agent into dist\attention-agent\attention-agent.exe
# Run from the desktop-agent folder with the venv active:
#   venv\Scripts\activate
#   .\build_agent.ps1

$ErrorActionPreference = "Stop"

pip install pyinstaller

pyinstaller --noconfirm --clean --onedir --name attention-agent `
  --hidden-import keyring.backends.Windows `
  --hidden-import win32timezone `
  agent_entry.py

if (-not (Test-Path "dist\attention-agent\attention-agent.exe")) {
  throw "Build failed: dist\attention-agent\attention-agent.exe not found"
}

Write-Host "Agent built: dist\attention-agent\attention-agent.exe"
Write-Host "Quick test:  dist\attention-agent\attention-agent.exe status"
