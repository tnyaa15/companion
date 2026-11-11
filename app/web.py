import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .bot import Companion
from .calendar import CalendarNotConfigured, GoogleCalendar
from .config import Settings
from .db import Database

log = logging.getLogger("companion.web")
STATIC_DIR = Path(__file__).resolve().parent / "static"


class TextInput(BaseModel):
    content: str = Field(min_length=1, max_length=300)


class ChatInput(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ReminderInput(BaseModel):
    content: str = Field(min_length=1, max_length=300)
    due_at: datetime


class CheckinInput(BaseModel):
    enabled: bool


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.load(
        require_bot_credentials=False, require_llm_api_key=False
    )
    database = Database(settings.db_path)
    companion = Companion(settings) if settings.llm_api_key else None
    calendar = GoogleCalendar(
        settings.google_calendar_token_file, settings.google_calendar_id
    )

    web = FastAPI(title="Nova Companion", docs_url=None, redoc_url=None)
    web.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"],
    )
    web.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @web.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @web.get("/api/state")
    def get_state():
        return {
            "profile": {
                "name": settings.user_name,
                "persona": settings.persona_name,
                "timezone": settings.timezone,
            },
            "connections": {
                "model_ready": bool(settings.llm_api_key),
                "provider": settings.llm_provider,
                "model": settings.llm_model,
                "telegram_ready": bool(settings.telegram_token and settings.owner_id),
                "discord_ready": bool(
                    settings.discord_bot_token and settings.discord_owner_id
                ),
                "calendar_ready": Path(settings.google_calendar_token_file).is_file(),
            },
            "checkin": {
                "enabled": database.get_preference("checkin_enabled", "1") == "1",
                "channel": settings.proactive_channel,
                "discord_target": "server" if settings.discord_channel_id else "dm",
                "max_per_day": settings.max_proactive_per_day,
                "quiet_start": settings.quiet_start,
                "quiet_end": settings.quiet_end,
            },
            "tasks": database.open_tasks(),
            "reminders": database.pending_reminders(),
            "memories": database.memories(),
            "messages": database.recent_messages(60),
        }

    @web.post("/api/chat")
    async def chat(payload: ChatInput):
        if companion is None:
            raise HTTPException(
                status_code=503,
                detail="Add an LLM API key to .env before starting a conversation.",
            )
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=422, detail="Message can't be empty.")
        reply = await companion.generate_reply(content)
        if not reply:
            raise HTTPException(status_code=502, detail="The model didn't return a reply.")
        return {"reply": reply}

    @web.post("/api/tasks", status_code=201)
    def add_task(payload: TextInput):
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=422, detail="Task can't be empty.")
        task_id = database.add_task(content)
        return {"id": task_id, "content": content}

    @web.patch("/api/tasks/{task_id}/done")
    def complete_task(task_id: int):
        if not database.complete_task(task_id):
            raise HTTPException(status_code=404, detail="Open task not found.")
        return {"ok": True}

    @web.delete("/api/tasks/{task_id}")
    def delete_task(task_id: int):
        if not database.delete_task(task_id):
            raise HTTPException(status_code=404, detail="Task not found.")
        return {"ok": True}

    @web.post("/api/reminders", status_code=201)
    def add_reminder(payload: ReminderInput):
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=422, detail="Reminder can't be empty.")
        zone = ZoneInfo(settings.timezone)
        due_local = payload.due_at
        if due_local.tzinfo is None:
            due_local = due_local.replace(tzinfo=zone)
        if due_local <= datetime.now(zone):
            raise HTTPException(status_code=422, detail="Choose a future time.")
        due_utc = due_local.astimezone(timezone.utc).isoformat()
        reminder_id = database.add_reminder(content, due_utc)
        return {"id": reminder_id, "content": content, "due_at": due_utc}

    @web.delete("/api/reminders/{reminder_id}")
    def cancel_reminder(reminder_id: int):
        if not database.cancel_reminder(reminder_id):
            raise HTTPException(status_code=404, detail="Pending reminder not found.")
        return {"ok": True}

    @web.post("/api/memories", status_code=201)
    def add_memory(payload: TextInput):
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=422, detail="Memory can't be empty.")
        if len(database.memories()) >= 20:
            raise HTTPException(status_code=409, detail="Memory list is full.")
        memory_id = database.add_memory(content)
        return {"id": memory_id, "content": content}

    @web.delete("/api/memories/{memory_id}")
    def delete_memory(memory_id: int):
        if not database.delete_memory(memory_id):
            raise HTTPException(status_code=404, detail="Memory not found.")
        return {"ok": True}

    @web.patch("/api/checkin")
    def set_checkin(payload: CheckinInput):
        database.set_preference("checkin_enabled", "1" if payload.enabled else "0")
        return {"enabled": payload.enabled}

    @web.get("/api/calendar")
    async def get_calendar():
        if not Path(settings.google_calendar_token_file).is_file():
            return {"connected": False, "events": []}
        try:
            events = await asyncio.to_thread(
                calendar.list_upcoming, datetime.now(timezone.utc), 8
            )
        except CalendarNotConfigured:
            return {"connected": False, "events": []}
        except Exception:
            log.exception("dashboard calendar lookup failed")
            raise HTTPException(status_code=502, detail="Calendar is unavailable.")
        return {
            "connected": True,
            "events": [
                {
                    "id": event.get("id", ""),
                    "summary": event.get("summary", "untitled event"),
                    "start": event.get("start", {}).get(
                        "dateTime", event.get("start", {}).get("date", "")
                    ),
                }
                for event in events
            ],
        }

    return web


app = create_app()