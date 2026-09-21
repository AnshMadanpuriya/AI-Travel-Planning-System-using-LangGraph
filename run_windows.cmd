@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo [VoyageGraph] uv is not installed.
  echo Install it with: winget install --id astral-sh.uv -e
  exit /b 1
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo [VoyageGraph] Created .env. Add your GROQ_API_KEY, save it, then run this file again.
  start "" notepad ".env"
  exit /b 1
)

findstr /C:"GROQ_API_KEY=your_groq_api_key" ".env" >nul
if not errorlevel 1 (
  echo [VoyageGraph] Replace the placeholder GROQ_API_KEY in .env first.
  start "" notepad ".env"
  exit /b 1
)

echo [VoyageGraph] Synchronizing the locked Python environment...
uv sync --locked
if errorlevel 1 exit /b 1

echo [VoyageGraph] Starting at http://localhost:8501
uv run --locked streamlit run frontend.py
