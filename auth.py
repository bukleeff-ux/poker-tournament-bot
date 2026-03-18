import hashlib
import hmac
import json
import urllib.parse
from typing import Optional

from config import BOT_TOKEN


def validate_init_data(init_data: str) -> Optional[dict]:
    """
    Validates Telegram WebApp initData.
    Returns parsed user dict if valid, None if invalid.
    """
    try:
        params = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = params.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )

        secret_key = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        user_str = params.get("user")
        if not user_str:
            return None

        return json.loads(urllib.parse.unquote(user_str))

    except Exception:
        return None
