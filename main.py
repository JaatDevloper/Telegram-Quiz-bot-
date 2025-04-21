import os
import asyncio
from telethon import TelegramClient, events
from aiohttp import web

# Hardcoded API credentials
api_id = 28624690
api_hash = "67e6593b5a9b5ab20b11ccef6700af5b"

client = TelegramClient("userbot", api_id, api_hash)

# --- Your quiz link watcher ---
@client.on(events.NewMessage(from_users="me", pattern="/watch"))
async def handle_watch(event):
    await event.respond("✅ Userbot is now watching for quiz links...")
    while True:
        try:
            if os.path.exists("userbot_inbox.txt"):
                with open("userbot_inbox.txt", "r") as f:
                    line = f.read().strip()
                if line:
                    link, outpath = line.split("|")
                    await process_quiz_link(link.strip(), outpath.strip())
                    os.remove("userbot_inbox.txt")
        except Exception as e:
            print(f"[Error] {e}")
        await asyncio.sleep(5)

# --- Dummy HTTP server to keep Koyeb alive ---
async def handle(request):
    return web.Response(text="Userbot is running.")

async def start_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

# --- Placeholder for actual quiz extraction ---
async def process_quiz_link(link, output_file):
    print(f"[INFO] Processing quiz link: {link}")
    # Replace with actual @QuizBot parsing logic
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Sample quiz content with ✅ answer marking.\n")

# --- Main async entry point ---
async def main():
    await client.start()
    print("✅ Telethon userbot started and ready.")
    await start_server()  # Keeps Koyeb happy
    await client.run_until_disconnected()

# Start everything
asyncio.run(main())
