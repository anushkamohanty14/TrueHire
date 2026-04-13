#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "✅ Environment setup complete."
echo "Run API:      uvicorn apps.api.src.main:app --reload"
echo "Run Streamlit: streamlit run apps/web/app.py"
echo "Run tests:    python -m unittest discover -s tests -p 'test_*.py' -v"
