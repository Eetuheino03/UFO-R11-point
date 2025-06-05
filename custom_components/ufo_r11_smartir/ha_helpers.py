try:
    from homeassistant.core import HomeAssistant  # type: ignore
except Exception:  # pragma: no cover - fallback for tests without Home Assistant
    class HomeAssistant:  # minimal stub
        pass

try:
    from homeassistant.util import dt as dt_util  # type: ignore
except Exception:  # pragma: no cover - fallback using standard datetime
    from datetime import datetime, timezone

    class dt_util:
        """Simplified replacement for Home Assistant's dt_util module."""

        @staticmethod
        def utcnow() -> datetime:
            """Return current UTC time."""
            return datetime.now(timezone.utc)
