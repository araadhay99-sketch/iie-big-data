"""Offline backup/restore. Stop Haven first; never include a backup in a public ZIP."""
from pathlib import Path
import argparse,json,hashlib,sqlite3,tempfile,zipfile,os,shutil
from locking import WorkspaceLock

def backup(data_dir,destination):
    data_dir=Path(data_dir).resolve();destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Destination already exists; choose a new backup filename.')
    if not (data_dir/'haven.sqlite3').is_file():raise ValueError('No Haven database found at source.')
    with WorkspaceLock(data_dir),tempfile.TemporaryDirectory() as tmp:
        copy=Path(tmp)/'haven.sqlite3'
        with sqlite3.connect(data_dir/'haven.sqlite3') as source,sqlite3.connect(copy) as target:source.backup(target)
        with sqlite3.connect(copy) as db:
            db.execute('DELETE FROM sessions');db.commit()
            blobs=[row[0] for row in db.execute('SELECT id FROM files')]
        paths=[('haven.sqlite3',copy)]+[('blobs/'+id,data_dir/'blobs'/id) for id in blobs]
        manifest={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths}
        try:
            with destination.open('xb') as stream:
                os.chmod(destination,0o600)
                with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
                    for name,path in paths:archive.write(path,name)
                    archive.writestr('manifest.json',json.dumps(manifest,indent=2))
        except:
            destination.unlink(missing_ok=True);raise
    return len(blobs)

def restore(archive_path,destination):
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Restore destination must not exist; existing data will not be overwritten.')
    with zipfile.ZipFile(archive_path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or 'manifest.json' not in names:raise ValueError('Invalid backup contents.')
        manifest=json.loads(archive.read('manifest.json'))
        if not isinstance(manifest,dict) or set(names)!=set(manifest)|{'manifest.json'} or 'haven.sqlite3' not in manifest:raise ValueError('Invalid manifest.')
        for name,digest in manifest.items():
            valid=name=='haven.sqlite3' or (name.startswith('blobs/') and len(name[6:])==32 and all(c in '0123456789abcdef' for c in name[6:]))
            if not valid or hashlib.sha256(archive.read(name)).hexdigest()!=digest:raise ValueError('Backup path/checksum validation failed.')
        destination.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
            stage=Path(tmp)/'restore';stage.mkdir(mode=0o700);(stage/'blobs').mkdir(mode=0o700)
            for name in manifest:
                p=stage/name;p.write_bytes(archive.read(name));p.chmod(0o600)
            with sqlite3.connect(stage/'haven.sqlite3') as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity check failed.')
                expected={'blobs/'+row[0] for row in db.execute('SELECT id FROM files')}
                if expected!={name for name in manifest if name.startswith('blobs/')}:raise ValueError('Backup has missing or unexpected blobs.')
                db.execute('DELETE FROM sessions');db.commit()
            stage.rename(destination)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['backup','restore']);parser.add_argument('source');parser.add_argument('destination')
    args=parser.parse_args()
    if args.operation=='backup':print('Backed up',backup(args.source,args.destination),'files. Keep this unencrypted archive private.')
    else:restore(args.source,args.destination);print('Restored. Sign in with the workspace password; old sessions were revoked.')
