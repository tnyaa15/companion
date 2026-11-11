# Companion (Phase 1)

A Telegram AI companion that texts like a friend, remembers the recent chat, and sends a
morning check-in on its own (with quiet hours, a daily cap, and a back-off if you ignore it).

## Stack

- Python 3.11+
- `python-telegram-bot` (long polling + built-in job queue, no server needed yet)
- Any OpenAI-compatible LLM API with a free tier (Groq or Gemini to start)
- SQLite (stdlib)

## Run it

1. Talk to **@BotFather** on Telegram, create a bot, copy the token.
2. Message **@userinfobot** to get your numeric Telegram id.
3. Get a free API key from your LLM provider (Groq or Google AI Studio).
4. Set up:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill it in
python main.py
```

5. Open your bot in Telegram, send `/start`, and talk.

## Tweak the personality

Edit `persona.md` and save. It is re-read on every message, so there is no restart needed.
Fill in the "About you" section at the bottom, because that's what makes it feel personal.

## Commands

- `/start` greeting
- `/remember <thing>` saves a fact you explicitly want remembered (up to 300 characters; 20 memories maximum)
- `/memories` lists saved facts
- `/forget_memory <id>` removes one saved fact
- `/forget` wipes chat history; saved facts are kept separately
- `/checkin` shows the daily check-in setting; `/checkin HH:MM` changes it; `/checkin off` and `/checkin on` pause or resume it
- `/remind YYYY-MM-DD HH:MM <what>` schedules a reminder in `TIMEZONE`
- `/reminders` lists pending reminders; `/cancel_reminder <id>` cancels one
- `/task <what>` adds a task; `/tasks` lists open tasks; `/done_task <id>` completes one; `/delete_task <id>` deletes one

Reminders are checked every 30 seconds. Reminders that become due during quiet hours are sent when quiet hours end. All scheduled jobs require the bot process to be running.

## Hosting note

Right now it only runs while `python main.py` is running. To get the "works when my laptop
is off" part, deploy it somewhere that stays awake. Free hosts that put apps to sleep after
inactivity will break the proactive messages, so look for an always-on free VM or a cheap
VPS (check current free-tier terms). A small Dockerfile and deployment come in the next step.

## Next steps

- Calendar integration (Google Calendar or Outlook) with confirmation before creating or changing events
- Optional search and other app integrations with explicit permissions
- Always-on hosting and a small web UI for memories, reminders, tasks, and settings
