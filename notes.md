uvicorn core.asgi:application --port 8000 --workers 4 --log-level debug --reload
./manage.py qcluster
