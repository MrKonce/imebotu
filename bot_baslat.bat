@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title TNKU IME ve Staj Telegram Botu
echo ========================================================
echo   TNKU IME ve Staj Telegram Bot Dinleyicisi
echo   Telegram'dan /rapor veya /tara yazabilirsiniz.
echo ========================================================
python main.py --listen
pause
