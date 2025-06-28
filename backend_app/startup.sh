#!/bin/bash
set -e  # Exit on any error

echo "=== SONIC BRIEF STARTUP SCRIPT ==="
echo "Current directory: $(pwd)"
echo "Current user: $(whoami)"
echo "Python version: $(python --version)"

# Change to the application directory
cd /home/site/wwwroot

echo "=== DIRECTORY CONTENTS ==="
ls -la

echo "=== LOOKING FOR REQUIREMENTS.TXT ==="
find . -name "requirements.txt" -type f -exec echo "Found: {}" \;

echo "=== UPGRADING PIP ==="
python -m pip install --upgrade pip

echo "=== INSTALLING DEPENDENCIES ==="
python -m pip install -r requirements.txt

echo "=== STARTING APPLICATION WITH GUNICORN + UVICORN ==="
echo "Command: python3 -m gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --reload --log-level debug"

# Start the application with Gunicorn and Uvicorn worker
exec python3 -m gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --reload --log-level debug

echo "=== INSTALLING DEPENDENCIES ==="
if [ -f "requirements.txt" ]; then
    echo "Installing from requirements.txt..."
    python -m pip install -r requirements.txt
else
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

echo "=== INSTALLED PACKAGES ==="
python -m pip list | grep -E "(fastapi|uvicorn|gunicorn)"

echo "=== CHECKING PYTHON PATH ==="
python -c "import sys; print('Python path:'); [print(f'  {p}') for p in sys.path]"

echo "=== TESTING IMPORTS ==="
python -c "
try:
    import app.main
    print('✓ app.main imported successfully')
except Exception as e:
    print(f'✗ Failed to import app.main: {e}')
    import traceback
    traceback.print_exc()
"

echo "=== STARTING APPLICATION ==="
python3 -m gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --log-level debug --access-logfile - --error-logfile -
