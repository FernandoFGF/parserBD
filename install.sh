python3 --version
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
[ -f config.py ] || cp config.example.py config.py
echo "Installation complete. Now edit config.py with your batch data."
