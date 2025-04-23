#!/bin/bash
pip install nest_asyncio telethon flask gunicorn python-dotenv
gunicorn --bind 0.0.0.0:$PORT --workers 1 main:app
