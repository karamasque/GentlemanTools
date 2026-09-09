@echo off
title GentlemanStation Discord Bot
color 0b
echo ===================================================
echo     GentlemanStation Discord VIP Bot Baslatiliyor
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/2] Gerekli Python kutuphaneleri kontrol ediliyor...
pip install -r requirements.txt

echo.
echo [2/2] Bot calistiriliyor...
python bot.py

pause
