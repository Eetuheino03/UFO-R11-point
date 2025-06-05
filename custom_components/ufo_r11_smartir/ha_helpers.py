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


try:
    import voluptuous as vol  # type: ignore
except Exception:  # pragma: no cover - fallback stub for tests without voluptuous

    class vol:
        """Simplified replacement for the voluptuous module."""

        @staticmethod
        def Schema(value):
            return value

        @staticmethod
        def Required(key, default=None):  # pylint: disable=unused-argument
            return key

        @staticmethod
        def Optional(key, default=None):  # pylint: disable=unused-argument
            return key

        @staticmethod
        def In(values):  # pylint: disable=unused-argument
            return lambda x: x


try:
    import aiofiles  # type: ignore
except Exception:  # pragma: no cover - fallback stub for tests without aiofiles

    class AsyncFileWrapper:
        def __init__(self, file_obj):
            self._file = file_obj

        async def read(self):
            return self._file.read()

        async def write(self, data):
            self._file.write(data)

        def __aiter__(self):
            async def _gen():
                for line in self._file:
                    yield line

            return _gen()

    class aiofiles:
        """Minimal aiofiles replacement."""

        @staticmethod
        def open(file, mode="r", encoding=None):  # pylint: disable=unused-argument
            class _AsyncContext:
                def __init__(self, path, m, enc):
                    self._path = path
                    self._mode = m
                    self._encoding = enc
                    self._fh = None

                async def __aenter__(self):
                    self._fh = open(self._path, self._mode, encoding=self._encoding)
                    return AsyncFileWrapper(self._fh)

                async def __aexit__(self, exc_type, exc, tb):
                    if self._fh:
                        self._fh.close()
                    return False

            return _AsyncContext(file, mode, encoding)
