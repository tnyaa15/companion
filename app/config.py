import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    owner_id: int
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    persona_name: str
    user_name: str
    timezone: str
    morning_hour: int
    morning_minute: int
    quiet_start: int
    quiet_end: int
    max_proactive_per_day: int
    history_turns: int
    db_path: str

    @staticmethod
    def load() -> "Settings":
        load_dotenv()
        env = os.environ
        return Settings(
            telegram_token=env["TELEGRAM_BOT_TOKEN"],
            owner_id=int(env["OWNER_TELEGRAM_ID"]),
            llm_api_key=env["LLM_API_KEY"],
            llm_base_url=env.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            llm_model=env.get("LLM_MODEL", "llama-3.3-70b-versatile"),
            persona_name=env.get("PERSONA_NAME", "Nova"),
            user_name=env.get("USER_NAME", "friend"),
            timezone=env.get("TIMEZONE", "Asia/Kolkata"),
            morning_hour=int(env.get("MORNING_HOUR", "8")),
            morning_minute=int(env.get("MORNING_MINUTE", "5")),
            quiet_start=int(env.get("QUIET_START", "23")),
            quiet_end=int(env.get("QUIET_END", "8")),
            max_proactive_per_day=int(env.get("MAX_PROACTIVE_PER_DAY", "3")),
            history_turns=int(env.get("HISTORY_TURNS", "30")),
            db_path=env.get("DB_PATH", "companion.db"),
        )
