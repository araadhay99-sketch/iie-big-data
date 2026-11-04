"""Start Haven on loopback by default. No external API or model required."""
import os
import uvicorn
if __name__=='__main__':
    uvicorn.run('app:create_app',factory=True,host=os.environ.get('HAVEN_BIND_HOST','127.0.0.1'),port=int(os.environ.get('HAVEN_PORT','7860')),log_level='info')
