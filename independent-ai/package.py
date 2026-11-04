"""Package source and fictional preview, excluding all owner data and environments."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parent
out=root/'dist';out.mkdir(exist_ok=True)
names=['README.md','STATUS.md','app.py','assistant.py','backup.py','locking.py','run.py','start.sh','requirements.txt','requirements-dev.txt','requirements-hosting.txt','wsgi.py','example-notes.md','package.py','.gitignore']
files=[(name,root/name) for name in names]
for folder in ['static','tests','deploy']:
    files.extend((p.relative_to(root).as_posix(),p) for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for name in ['cloud-chat.png','cloud-browser-results.json','chat.png','files.png','mobile.png','setup.png','browser-results.json']:
    p=root/'artifacts'/name
    if p.exists():files.append(('preview/'+name,p))
manifest={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in files}
archive=out/'haven-private-ai.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name,p in files:z.write(p,'Haven/'+name)
    z.writestr('Haven/manifest.sha256.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert not any('/data/' in n or '/.venv/' in n or '__pycache__' in n for n in z.namelist())
    for name,digest in manifest.items():assert hashlib.sha256(z.read('Haven/'+name)).hexdigest()==digest
print(json.dumps({'package':str(archive),'bytes':archive.stat().st_size,'files':len(files),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2))
