"""Prepare a loopback-only, bounded server command after verifying local weights."""
import json
from .budget import Budget
from .model import ModelError,digest

def server_command(root,manifest):
    budget=Budget(root);budget.require_bytes(0)
    model=budget.safe_path('models/'+manifest['filename'])
    if not model.is_file():raise ModelError('Model weights are not installed. No reasoning server has been started.')
    if model.stat().st_size!=manifest['size_bytes'] or digest(model)!=manifest['sha256']:
        raise ModelError('Local model checksum/size did not verify. No server was started.')
    path=budget.safe_path('runtime/installed.json')
    if not path.is_file():raise ModelError('Verified inference runtime is not installed.')
    record=json.loads(path.read_text());server=budget.safe_path(record.get('server_path',''))
    if not record.get('checksum_verified') or not record.get('runtime_smoke_verified') or not server.is_file():
        raise ModelError('Runtime verification record is incomplete.')
    return [str(server),'-m',str(model),'--alias',manifest.get('pilot_alias','kaisen-qwen3-8b-q4'),
            '--host','127.0.0.1','--port','8081','--jinja','--parallel','1',
            '--ctx-size','8192','--threads','4','--n-predict','2048','--n-gpu-layers','0']
