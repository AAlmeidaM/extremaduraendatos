@echo off
cd /d "%~dp0"
> "_ejecucion_claude\herramientas.txt" (
echo === git ===
where git
git --version
git config --global credential.helper
git remote -v
echo === node ===
where node
node --version
where npm
call npm --version
echo === gh ===
where gh
echo === vercel ===
where vercel
echo === winget ===
where winget
)
2>&1 >> "_ejecucion_claude\herramientas.txt" echo.
echo HECHO > "_ejecucion_claude\herramientas_estado.txt"
