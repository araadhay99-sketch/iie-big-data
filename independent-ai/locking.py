"""Single-process workspace lock for the supported Linux deployment."""
from pathlib import Path
import fcntl

class WorkspaceLock:
    def __init__(self,directory):
        self.handle=(Path(directory)/'server.lock').open('a+b')
        try:fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            raise ValueError('This workspace is already open. Stop its server before another server or backup.')
    def close(self):
        if not self.handle.closed:
            fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN);self.handle.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
