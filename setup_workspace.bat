@echo off
echo ==========================================
echo   JingDi Project - Auto Setup Workspace
echo ==========================================

echo [1/4] Checking Python Dependencies...
pip install -r backend/requirements.txt

echo.
echo [2/4] Checking/Installing Vercel CLI...
cmd /c npm install -g vercel

echo.
echo [3/4] Preparation for Vercel...
echo Starting Vercel login...
cmd /c vercel login
echo Starting Vercel link...
cmd /c vercel link

echo.
echo [4/4] Environment Reminder
echo ******************************************
echo IMPORTANT: Please make sure you have the .env file 
echo in the 'backend' folder. 
echo If you don't have it, copy it from your other machine.
echo ******************************************

echo Setup Complete! 🚀
pause
