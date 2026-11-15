@echo off
chcp 65001 >nul
title Enterprise Tax Co-Pilot Starter
echo ===================================================
echo   Enterprise Tax Co-Pilot (VAT Registration)
echo   กำลังเริ่มต้นระบบทั้ง 3 ส่วน...
echo ===================================================

:: 1. Start Ollama
echo [1/3] กำลังเริ่ม Ollama Local LLM...
start "Ollama Server" /min cmd /c "ollama serve"

:: 2. Start FastAPI Backend
echo [2/3] กำลังเริ่ม FastAPI Backend (Port 8000)...
cd /d "%~dp0backend"
start "VAT Backend (Port 8000)" /min cmd /c ".\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

:: 3. Start Next.js Frontend (ต้องสั่ง npm run build ในโฟลเดอร์ frontend ก่อนครั้งแรก)
echo [3/3] กำลังเริ่ม Web Frontend (Port 3000)...
cd /d "%~dp0frontend"
start "VAT Frontend (Port 3000)" /min cmd /c "npm start"

echo.
echo รอระบบเปิด 15 วินาที...
timeout /t 15 >nul

echo กำลังเปิดเบราว์เซอร์ไปที่ http://localhost:3000/chat ...
start http://localhost:3000/chat

echo ===================================================
echo   ระบบพร้อมใช้งานแล้วที่ http://localhost:3000/chat
echo ===================================================
timeout /t 5
