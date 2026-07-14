@echo off
echo [1/3] Activating Virtual Environment...
call venv\Scripts\activate

echo [2/3] Cleaning old build files...
if exist build rd /s /q build
if exist dist rd /s /q dist

echo [3/3] Packaging AcaDesk.exe (This may take 2-3 minutes)...
pyinstaller --noconsole --onefile ^
--add-data "ui;ui" ^
--add-data "logic;logic" ^
--add-data "icon.ico;." ^
--add-data "AcaDesk (2).png;." ^
--add-data "venv\Lib\site-packages\customtkinter;customtkinter/" ^
--icon="icon.ico" ^
--hidden-import "pyodbc" ^
--hidden-import "psycopg2" ^
--hidden-import "oracledb" ^
-n "AcaDesk" main.py

echo Done! Your app is ready in the 'dist' folder.
pause