"""Logical-byte quota for cooperating managed writers, not a kernel quota.

External/manual filesystem writes cannot be controlled by this protocol.
Shared system packages are outside the project allowance.
"""

import fcntl
import os
import stat
from contextlib import contextmanager
from pathlib import Path


class BudgetError(ValueError):
    """A write would exceed the configured storage allowance."""


class Budget:
    def __init__(self, root, max_bytes=20_000_000_000):
        self.root = Path(os.path.abspath(root))
        self.max_bytes = int(max_bytes)
        if self.max_bytes < 0:
            raise ValueError("max_bytes must be nonnegative")
        self.safe_path(".")

    def safe_path(self, relative_path):
        """Return a project path only when no existing component is a symlink."""
        path = Path(os.path.abspath(self.root / relative_path))
        if not path.is_relative_to(self.root):
            raise ValueError("Write path must stay inside the project")
        for component in (path, *path.parents):
            if component.is_symlink():
                raise ValueError("Symlink write paths are not allowed")
        return path

    def used_bytes(self):
        self.safe_path(".")
        total = 0
        def fail(error):
            raise error
        for directory, dirs, files in os.walk(self.root, followlinks=False, onerror=fail):
            dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
            for name in files:
                info = (Path(directory) / name).lstat()
                if stat.S_ISREG(info.st_mode):
                    total += info.st_size
        return total

    def require_bytes(self, additional):
        additional = int(additional)
        if additional < 0:
            raise ValueError("additional must be nonnegative")
        used = self.used_bytes()
        if used + additional > self.max_bytes:
            raise BudgetError(f"Project storage budget exceeded: {used} + {additional} > {self.max_bytes} bytes")
        return self.max_bytes - used

    @contextmanager
    def writer(self):
        """Serialize managed writes across processes; fail immediately if busy."""
        self.safe_path(".").mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = self.safe_path(".storage.lock")
        handle = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(handle).st_mode):
                raise ValueError("Storage lock must be a regular file")
            os.fchmod(handle, 0o600)
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise BudgetError("Another managed storage writer is active; retry after it finishes") from error
            yield
        finally:
            # Keep the lock inode in place so every writer coordinates on it.
            os.close(handle)
