import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    owner_id: int
    llm_api_key: str
    llm_provider: str
    llm_base_url: str
    llm_model: str
    persona_name: str
    user_name: str
    timezone: str
    quiet_start: int
    quiet_end: int
    max_proactive_per_day: int
    proactive_channel: str
    history_turns: int
    db_path: str
    google_calendar_token_file: str
    google_calendar_id: str
    discord_bot_token: str | None
    discord_owner_id: int | None

    @staticmethod
    def load() -> "Settings":
        load_dotenv()
        env = os.environ
        discord_owner_id = env.get("DISCORD_OWNER_ID", "").strip()
        llm_provider = env.get("LLM_PROVIDER", "groq").strip().lower()
        default_base_urls = {
            "groq": "https://api.groq.com/openai/v1",
            "openai-compatible": "https://api.groq.com/openai/v1",
            "openai": "https://api.openai.com/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "anthropic": "",
            "claude": "",
        }
        return Settings(
            telegram_token=env["TELEGRAM_BOT_TOKEN"],
            owner_id=int(env["OWNER_TELEGRAM_ID"]),
            llm_api_key=env["LLM_API_KEY"],
            llm_provider=llm_provider,
            llm_base_url=env.get("LLM_BASE_URL") or default_base_urls.get(
                llm_provider, ""
            ),
            llm_model=env.get("LLM_MODEL", "llama-3.3-70b-versatile"),
            persona_name=env.get("PERSONA_NAME", "Nova"),
            user_name=env.get("USER_NAME", "friend"),
            timezone=env.get("TIMEZONE", "Asia/Kolkata"),
            quiet_start=int(env.get("QUIET_START", "23")),
            quiet_end=int(env.get("QUIET_END", "8")),
            max_proactive_per_day=int(env.get("MAX_PROACTIVE_PER_DAY", "3")),
            proactive_channel=env.get("PROACTIVE_CHANNEL", "telegram").strip().lower(),
            history_turns=int(env.get("HISTORY_TURNS", "30")),
            db_path=env.get("DB_PATH", "companion.db"),
            google_calendar_token_file=env.get(
                "GOOGLE_CALENDAR_TOKEN_FILE", "google-calendar-token.json"
            ),
            google_calendar_id=env.get("GOOGLE_CALENDAR_ID", "primary"),
            discord_bot_token=env.get("DISCORD_BOT_TOKEN") or None,
            discord_owner_id=int(discord_owner_id) if discord_owner_id else None,
        )
