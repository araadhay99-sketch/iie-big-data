"""Compatibility entry point for traditional single-worker WSGI hosting.

Provider config imports create_wsgi_application AFTER setting server-only HAVEN_*
variables. No hosted account or public route is created by this module.
"""
import asyncio,atexit,threading
from a2wsgi import ASGIMiddleware
from app import create_app

class WSGIApplication:
    def __init__(self,settings=None):
        self.api=create_app(settings)
        self.loop=asyncio.new_event_loop()
        self.thread=threading.Thread(target=self.loop.run_forever,daemon=True)
        self.thread.start()
        self.gateway=ASGIMiddleware(self.api,wait_time=10,loop=self.loop)
        self.closed=False
        atexit.register(self.close)
    def __call__(self,environ,start_response):return self.gateway(environ,start_response)
    def close(self):
        if self.closed:return
        self.closed=True
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)
        if not self.thread.is_alive():self.loop.close()
        self.api.state.store.close()

def create_wsgi_application(settings=None):return WSGIApplication(settings)
