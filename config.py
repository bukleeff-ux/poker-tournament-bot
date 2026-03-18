import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Comma-separated list of admin Telegram user IDs (e.g. "123456,789012")
_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(x) for x in _admin_ids_raw.split(",") if x.strip()]

# Public HTTPS URL where the Mini App is hosted (e.g. ngrok / Cloudflare Tunnel URL)
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")

POINTS = {1: 3, 2: 2, 3: 1}

MEDAL_EMOJI = {1: "🥇", 2: "🥈", 3: "🥉"}
PLACE_LABEL = {1: "1st place", 2: "2nd place", 3: "3rd place"}
