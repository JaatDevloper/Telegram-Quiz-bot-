worker: bash setup.sh && python main.py
web: pip install nest_asyncio telethon && gunicorn --bind 0.0.0.0:$PORT --workers 1 main:app
