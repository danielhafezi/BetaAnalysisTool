@echo off
pip install --user --upgrade --force-reinstall --no-warn-script-location --ignore-installed -r requirements.txt
streamlit run main.py
pause
