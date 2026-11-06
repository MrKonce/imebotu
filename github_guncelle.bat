@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title TNKU IME Botu - GitHub & Render Otomatik Guncelleme
echo ========================================================
echo   TNKU IME Botu - GitHub ve Render Otomatik Guncelleyici
echo ========================================================
echo.
echo [*] Yerel dosya degisiklikleri paketleniyor...
git add .
git commit -m "Bot guncellemesi: Lokasyon ve stajyer/IME filtresi iyilestirildi"
echo.
echo [*] GitHub'a gonderiliyor (git push)...
git push origin main
if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo   [BASARILI] Guncellemeler GitHub'a aktarildi!
    echo   Render.com 1-2 dakika icinde yeni kodu otomatik cekip
    echo   botunuzu bulutta yenileyecektir.
    echo ========================================================
) else (
    echo.
    echo [BILGI] Eger git push hata verirse, degisiklikleri
    echo GitHub web sitesinden 'Add file > Upload files' ile de yukleyebilirsiniz.
)
echo.
pause
