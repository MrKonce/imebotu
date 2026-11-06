$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  TNKÜ İME ve Uzun Dönem Staj Bulma Robotu" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

python main.py --once
