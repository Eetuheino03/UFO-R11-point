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


def open(file, mode="r", encoding=None):  # type: ignore
    class _AsyncContext:
        def __init__(self, path, m, enc):
            self._path = path
            self._mode = m
            self._encoding = enc
            self._fh = None

        async def __aenter__(self):
            self._fh = __builtins__["open"](
                self._path, self._mode, encoding=self._encoding
            )
            return AsyncFileWrapper(self._fh)

        async def __aexit__(self, exc_type, exc, tb):
            if self._fh:
                self._fh.close()
            return False

    return _AsyncContext(file, mode, encoding)
