# Companion

A personal AI companion with natural chat and context-aware check-ins. It only considers
checking in after a real conversation has gone quiet, and respects quiet hours, a daily cap,
and back-off when messages go unanswered.

## Stack

- Python 3.11+
- `python-telegram-bot` (long polling + built-in job queue, no server needed yet)
- Groq, OpenAI, Gemini, or Anthropic model APIs
- SQLite (stdlib)
- Optional Google Calendar and Discord integrations

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
- `/checkin` or `/checkin status` shows adaptive check-in status; `/checkin off` and `/checkin on` pause or resume it
- `/remind YYYY-MM-DD HH:MM <what>` schedules a reminder in `TIMEZONE`
- `/reminders` lists pending reminders; `/cancel_reminder <id>` cancels one
- `/task <what>` adds a task; `/tasks` lists open tasks; `/done_task <id>` completes one; `/delete_task <id>` deletes one

Reminders are checked every 30 seconds. Reminders that become due during quiet hours are sent when quiet hours end. All scheduled jobs require the bot process to be running.

## Adaptive check-ins

The companion checks its recent conversation every 30 minutes, but only asks the model to consider a message after a user conversation has been quiet for at least 90 minutes. It evaluates each latest user message once, only sends if the model returns a useful check-in, and respects quiet hours, the daily cap, a four-hour cooldown, and back-off after two unanswered proactive messages. This is a context-based policy, not a human feeling; it won't invent current news or claim it was thinking while offline.

Set `PROACTIVE_CHANNEL=telegram` or `PROACTIVE_CHANNEL=discord` to choose where check-ins and reminders are delivered. Telegram is the default; Discord requires both Discord settings to be configured.

## Model APIs

Set `LLM_PROVIDER` to `groq`, `openai`, `gemini`, or `anthropic`, then set `LLM_API_KEY` and `LLM_MODEL` for that provider. OpenAI and Gemini use their OpenAI-compatible chat endpoints; Anthropic uses its native Messages API. Leave `LLM_BASE_URL` blank for the provider default, or set it for a compatible endpoint. A ChatGPT or Claude subscription does not include API usage. Free tiers and model availability can change; OpenAI and Anthropic API usage is typically billed separately.

## Google Calendar

The integration requests only the Calendar events scope, not Gmail. Create a Google OAuth client for a Desktop app, save its JSON as `client_secret.json`, set up the consent screen, and add your account as a test user. Run `python -m app.calendar_auth` to authorize and store the local refresh token. Google OAuth apps left in Testing can receive refresh tokens that expire after seven days; for long-running use, move the consent app to Production and complete any verification Google requires for the requested scope. Keep both JSON files private; they are ignored by Git.

- `/calendar` lists upcoming events
- `/event YYYY-MM-DD HH:MM HH:MM <title>` prepares an event and asks for confirmation before writing it

Set `GOOGLE_CALENDAR_ID=primary` or the ID of another calendar you can access. Standard Google Calendar API use is currently no-cost under its published quota threshold; review Google's current quota and billing terms before deployment.

## Discord

Create a Discord application and bot, enable **Message Content Intent**, then set `DISCORD_BOT_TOKEN` and your numeric `DISCORD_OWNER_ID`. Install the bot in a private server with only the channel permissions it needs: view/read messages, send messages, and attach files. The bot ignores everyone except that configured user. Normal text uses the same conversation history as Telegram.

To send an image or video, put it in the local `media/` folder and use `!sendmedia <filename>` in Discord. The folder is ignored by Git. Incoming images and videos are not analyzed yet; the bot will say so rather than pretend it saw their contents.

## Hosting note

Right now it only runs while `python main.py` is running. To get the "works when my laptop
is off" part, deploy it somewhere that stays awake. Free hosts that put apps to sleep after
inactivity will break the proactive messages, so look for an always-on free VM or a cheap
VPS (check current free-tier terms). A small Dockerfile and deployment come in the next step.

## Next steps

- News via selected RSS feeds or a search provider, so proactive news suggestions use real sources
- Image/video understanding or generation, using a chosen multimodal API
- Always-on hosting and a small web UI for memories, reminders, tasks, and settings
