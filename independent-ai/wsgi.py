"""Compatibility entry point for traditional single-worker WSGI hosting.

Provider config imports create_wsgi_application AFTER setting server-only HAVEN_*
variables. No hosted account or public route is created by this module.
"""
import asyncio,atexit,os,threading
from a2wsgi import ASGIMiddleware
from app import create_app

class WSGIApplication:
    def __init__(self,settings=None):
        # A prefork host imports this module in its master process. Threads do
        # not survive fork, and opening the store here also shares its flock.
        self.settings=settings
        self.api=self.loop=self.thread=self.gateway=None
        self._pid=None
        self._lock_pid=os.getpid()
        self._lock=threading.RLock()
        self.closed=False
        atexit.register(self.close)

    def _process(self):
        pid=os.getpid()
        if self._pid is not None and self._pid!=pid:
            raise RuntimeError('A started WSGI application cannot be reused in another process.')
        if self._lock_pid!=pid:
            # Only an unstarted instance may be inherited. Replace its mutex
            # before using it; an inherited mutex may have lost its owner.
            self._lock=threading.RLock()
            self._lock_pid=pid
        return pid

    def _initialize(self):
        pid=self._process()
        with self._lock:
            if self.closed:raise RuntimeError('This WSGI application is closed.')
            if self.gateway is not None:return
            self._pid=pid
            try:
                self.api=create_app(self.settings)
                self.loop=asyncio.new_event_loop()
                self.thread=threading.Thread(target=self.loop.run_forever,daemon=True)
                self.thread.start()
                self.gateway=ASGIMiddleware(self.api,wait_time=10,loop=self.loop)
            except BaseException:
                self._release()
                raise

    def __call__(self,environ,start_response):
        self._initialize()
        return self.gateway(environ,start_response)

    def _release(self):
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self.loop.stop)
            if self.thread is not None and self.thread.ident is not None:
                self.thread.join(timeout=5)
            if self.thread is None or not self.thread.is_alive():self.loop.close()
        if self.api is not None:self.api.state.store.close()
        self.api=self.loop=self.thread=self.gateway=None

    def close(self):
        # LOCK_UN in a child would release the parent's inherited flock too.
        if self._pid is not None and self._pid!=os.getpid():return
        self._process()
        with self._lock:
            if self.closed:return
            self.closed=True
            self._release()
            atexit.unregister(self.close)

def create_wsgi_application(settings=None):return WSGIApplication(settings)
