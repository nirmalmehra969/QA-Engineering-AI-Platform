@echo off
echo ===================================================
echo  Launching Java + Selenium + TestNG Automation Run
echo ===================================================
cd /d "%~dp0"
mvn clean test -DbaseUrl=http://127.0.0.1:5000/app/target-store
pause
