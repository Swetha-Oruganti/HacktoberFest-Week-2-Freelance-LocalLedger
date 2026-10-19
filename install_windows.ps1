$ErrorActionPreference = 'Stop'
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Write-Host 'Install Tesseract OCR and Ollama separately; see README.md for setup.'
Write-Host 'Then run: .\.venv\Scripts\streamlit.exe run app.py'
