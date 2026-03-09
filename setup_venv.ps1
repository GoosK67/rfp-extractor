
Param(
 [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
Write-Host "[+] Creating venv ..."
& $Python -m venv .venv
Write-Host "[+] Activating venv in this session ..."
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& ".\.venv\Scripts\Activate.ps1"
Write-Host "[+] Upgrading pip ..."
python -m pip install --upgrade pip
Write-Host "[+] Installing requirements ..."
python -m pip install -r requirements.txt
Write-Host "[OK] venv ready."
