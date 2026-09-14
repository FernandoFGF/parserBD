@echo off
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist config.py copy config.example.py config.py
echo.
echo Installation complete. Now edit config.py with your batch data.
pause
