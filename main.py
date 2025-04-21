import asyncio
import os
import re
from telethon import TelegramClient, events

api_id = int(os.getenv("API_ID", "28624690"))
api_hash = os.getenv("API_HASH", "67e6593b5a9b5ab20b11ccef6700af5b")
bot_username = "QuizBot"

client = TelegramClient("quizuserbot", api_id, api_hash)

async def process_quiz_link(link, output_file):
    start_param = link.split("start=")[1]
    quiz_text = ""

    async with client.conversation(bot_username, timeout=120) as conv:
        await conv.send_message(f"/start {start_param}")

        for _ in range(50):
            res = await conv.get_response()
            if res.buttons:
                question = res.text
                quiz_text += f"{question}\n"
                for row in res.buttons:
                    for btn in row:
                        text = btn.text.strip()
                        mark = "✅" if "✅" in text else ""
                        clean = re.sub("✅", "", text).strip()
                        quiz_text += f"{clean} {mark}\n"
                quiz_text += "\n"

                try:
                    await res.click(text="Next")
                except:
                    break
            else:
                break

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(quiz_text)

@client.on(events.NewMessage(from_users="me", pattern="/watch"))
async def watcher(event):
    await event.respond("✅ Watching for quiz links...")
    while True:
        try:
            if os.path.exists("userbot_inbox.txt"):
                with open("userbot_inbox.txt", "r") as f:
                    line = f.read().strip()
                if line:
                    link, outpath = line.split("|")
                    await process_quiz_link(link, outpath)
                    os.remove("userbot_inbox.txt")
        except Exception as e:
            print(f"[error] {e}")
        await asyncio.sleep(5)

print("Starting Telethon client...")
client.start()
client.loop.run_forever()

