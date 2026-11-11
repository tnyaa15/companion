from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class CalendarNotConfigured(RuntimeError):
    pass


class GoogleCalendar:
    def __init__(self, token_path: str, calendar_id: str):
        self.token_path = Path(token_path)
        self.calendar_id = calendar_id

    def _service(self):
        if not self.token_path.exists():
            raise CalendarNotConfigured(
                "Calendar is not connected yet. Add your OAuth client file and run "
                "python -m app.calendar_auth."
            )

        try:
            credentials = Credentials.from_authorized_user_file(
                str(self.token_path), CALENDAR_SCOPES
            )
        except (OSError, ValueError) as exc:
            raise CalendarNotConfigured(
                "Calendar authorization is invalid. Run python -m app.calendar_auth again."
            ) from exc

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            self.token_path.write_text(credentials.to_json(), encoding="utf-8")
        if not credentials.valid:
            raise CalendarNotConfigured(
                "Calendar authorization expired. Run python -m app.calendar_auth again."
            )
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def list_upcoming(self, time_min: datetime, max_results: int = 8) -> list[dict]:
        if time_min.tzinfo is None:
            raise ValueError("time_min must be timezone-aware")
        response = (
            self._service()
            .events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min.astimezone(timezone.utc).isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return response.get("items", [])

    def create_event(
        self,
        summary: str,
        start_at: datetime,
        end_at: datetime,
        timezone_name: str,
    ) -> dict:
        if start_at.tzinfo is None or end_at.tzinfo is None:
            raise ValueError("event start and end must be timezone-aware")
        body = {
            "summary": summary,
            "start": {"dateTime": start_at.isoformat(), "timeZone": timezone_name},
            "end": {"dateTime": end_at.isoformat(), "timeZone": timezone_name},
        }
        return (
            self._service()
            .events()
            .insert(calendarId=self.calendar_id, body=body)
            .execute()
        )