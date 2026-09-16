@echo off
rem Conecta el repositorio local con GitHub y sube el codigo (2026-09-16)
cd /d "%~dp0"
if not exist "_ejecucion_claude" mkdir "_ejecucion_claude"
> "_ejecucion_claude\github.txt" echo === INICIO %date% %time% ===
git remote get-url origin >nul 2>&1 || git remote add origin https://github.com/AAlmeidaM/extremaduraendatos.git
git remote set-url origin https://github.com/AAlmeidaM/extremaduraendatos.git
git branch -M main >> "_ejecucion_claude\github.txt" 2>&1
git push -u origin main >> "_ejecucion_claude\github.txt" 2>&1
echo %errorlevel% > "_ejecucion_claude\github_estado.txt"
git remote -v >> "_ejecucion_claude\github.txt" 2>&1
git log --oneline -3 >> "_ejecucion_claude\github.txt" 2>&1
>> "_ejecucion_claude\github.txt" echo === FIN %date% %time% ===
