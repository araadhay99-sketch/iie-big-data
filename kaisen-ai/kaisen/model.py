"""Revision-pinned, size- and checksum-verified optional model installation."""
import hashlib,json,re,os
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urlsplit
from urllib.error import HTTPError,URLError
from .budget import Budget

class ModelError(Exception):pass

class HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        parsed=urlsplit(newurl)
        if parsed.scheme!='https' or parsed.username or parsed.password:
            raise ModelError('Model redirects must preserve HTTPS without embedded credentials.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def load_manifest(path):
    value=json.loads(Path(path).read_text())
    if (not re.fullmatch(r'[0-9a-f]{40}',value.get('revision',''))
            or not re.fullmatch(r'[0-9a-f]{64}',value.get('sha256',''))
            or type(value.get('size_bytes')) is not int or not 0<value['size_bytes']<20_000_000_000
            or Path(value.get('filename','')).name!=value.get('filename')
            or not value.get('filename','').endswith('.gguf')):
        raise ModelError('Invalid pinned model metadata.')
    url=urlsplit(value.get('download_url',''))
    if url.scheme!='https' or url.hostname!='huggingface.co' or url.username or url.password or url.query or url.fragment:
        raise ModelError('Model URL must use the approved publisher HTTPS host.')
    return value

def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()

def install_model(root,manifest,opener=None,budget=None):
    budget=budget or Budget(root)
    with budget.writer():
        return _install_model(root,manifest,opener,budget)

def _install_model(root,manifest,opener,budget):
    root=Path(root);budget=budget or Budget(root)
    target=budget.safe_path('models/'+manifest['filename'])
    target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if target.exists():
        if target.stat().st_size==manifest['size_bytes'] and digest(target)==manifest['sha256']:
            return {'installed':True,'checksum_verified':True,'downloaded_now':False}
        raise ModelError('Existing model differs; it was preserved without overwrite.')
    budget.require_bytes(manifest['size_bytes']+1024*1024)
    temporary=budget.safe_path('models/'+manifest['filename']+'.part')
    if temporary.exists():raise ModelError('A partial model already exists; inspect it before retrying.')
    opener=opener or build_opener(HTTPSRedirects())  # Inherit proxy and CA trust.
    count=0;checksum=hashlib.sha256()
    try:
        with opener.open(Request(manifest['download_url'],headers={'Accept':'application/octet-stream'}),timeout=30) as response:
            declared=response.headers.get('Content-Length')
            if declared is not None and int(declared)!=manifest['size_bytes']:raise ModelError('Publisher download size differs from pinned metadata.')
            with temporary.open('xb') as output:
                temporary.chmod(0o600)
                while chunk:=response.read(1024*1024):
                    count+=len(chunk)
                    if count>manifest['size_bytes']:raise ModelError('Model exceeded its pinned size.')
                    budget.require_bytes(len(chunk))
                    checksum.update(chunk);output.write(chunk)
                output.flush();os.fsync(output.fileno())
        if count!=manifest['size_bytes'] or checksum.hexdigest()!=manifest['sha256']:
            raise ModelError('Model checksum or complete-file size did not verify.')
        temporary.replace(target)
        return {'installed':True,'checksum_verified':True,'downloaded_now':True,'bytes':count}
    except (HTTPError,URLError,TimeoutError):
        raise ModelError('Model download unavailable. Check approved publisher/CDN networking and retry only after a meaningful change.') from None
    finally:temporary.unlink(missing_ok=True)

def model_status(root,manifest):
    target=Budget(root).safe_path('models/'+manifest['filename'])
    return {'publisher_metadata_verified':True,'file_present':target.is_file(),
            'pinned_bytes':manifest['size_bytes'],'file_size_matches':target.is_file() and target.stat().st_size==manifest['size_bytes'],
            'local_checksum_verified':False,'inference_verified':False}
