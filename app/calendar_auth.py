import os
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

from .calendar import CALENDAR_SCOPES


def main() -> None:
    load_dotenv()
    client_path = Path(os.getenv("GOOGLE_OAUTH_CLIENT_FILE", "client_secret.json"))
    token_path = Path(os.getenv("GOOGLE_CALENDAR_TOKEN_FILE", "google-calendar-token.json"))
    if not client_path.is_file():
        raise SystemExit(
            f"OAuth client file not found: {client_path}. "
            "Create a Desktop app OAuth client and place its JSON file here."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(client_path), CALENDAR_SCOPES)
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    print(f"Calendar connected. Token stored at {token_path}; keep it private.")


if __name__ == "__main__":
    main()