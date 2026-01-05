@echo off
pip install --user --upgrade --no-warn-script-location -r requirements.txt
python -m streamlit run main.py
pause
