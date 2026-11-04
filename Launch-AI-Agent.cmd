@echo off
title AXIOM Industrial Digital Twin AI Agent Hub
cd /d "C:\Users\Satyarth\.gemini\antigravity\scratch\industrial-twin-agent"
echo ========================================================
echo   AXIOM INDUSTRIAL DIGITAL TWIN AI AGENT HUB
echo   Powered by Google Gemini AI & Python FastAPI
echo ========================================================
echo.
echo Starting AI Agent Server on http://127.0.0.1:8990 ...
echo Database Bridge: C:\Users\Satyarth\Desktop\industrial-digital-twin\backend\data\portal.sqlite3
echo.
C:\Python313\python.exe run_agent.py
pause
