"""Read-only PythonAnywhere account checks; never prints or saves credentials."""
import argparse,json,os,re,sys
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError

HOST='www.pythonanywhere.com'
class RefuseRedirects(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise HTTPError(req.full_url,code,'Redirect refused to protect account credentials.',headers,fp)

class Account:
    def __init__(self,username,token,opener=None):
        if not re.fullmatch(r'[A-Za-z0-9_]{1,30}',username or ''):raise ValueError('Invalid or missing PythonAnywhere username.')
        if not token:raise ValueError('PA_API_TOKEN is not configured. Enter it in secure environment settings, never in chat.')
        if '\r' in token or '\n' in token:raise ValueError('The configured API token contains a line break.')
        self.username=username;self._token=token;self._opener=opener or build_opener(RefuseRedirects())
    def read(self,resource):
        if resource not in ('cpu','webapps'):raise ValueError('This preflight permits only CPU and webapp metadata reads.')
        url=f'https://{HOST}/api/v0/user/{self.username}/{resource}/'
        req=Request(url,headers={'Authorization':'Token '+self._token,'Accept':'application/json'},method='GET')
        try:
            with self._opener.open(req,timeout=20) as response:
                body=response.read(200001)
                if len(body)>200000:raise ValueError('Provider metadata response exceeded the safe size limit.')
                return json.loads(body)
        except HTTPError as error:
            raise ValueError(f'PythonAnywhere {resource} check returned HTTP {error.code}; no response body or credential was logged.') from None
        except (URLError,TimeoutError):raise ValueError('Could not reach the configured PythonAnywhere API; check network and binding readiness.') from None
        except (json.JSONDecodeError,UnicodeDecodeError):raise ValueError('Provider did not return valid JSON metadata.') from None
    def preflight(self):
        cpu=self.read('cpu');webapps=self.read('webapps')
        if not isinstance(cpu,dict) or not isinstance(webapps,list):raise ValueError('Unexpected account metadata shape; no configuration changes made.')
        fields=('domain_name','python_version','source_directory','virtualenv_path','force_https')
        safe_webapps=[{key:app.get(key) for key in fields if key in app} for app in webapps if isinstance(app,dict)]
        return {'username':self.username,'host':HOST,'read_only':True,'api_authenticated':True,
                'cpu':{key:cpu[key] for key in ('daily_cpu_limit_seconds','daily_cpu_usage_seconds','daily_cpu_total_usage_seconds','next_reset_time') if key in cpu},
                'webapps':safe_webapps,'existing_webapps':len(webapps),
                'limitations':['This does not verify free-tier billing, available disk, package compatibility, live HTTPS, or persistent recovery.','No console, webapp, file or billing configuration was created or modified.']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username',default=os.environ.get('PA_USERNAME',''))
    parser.add_argument('--report',type=Path,help='Optional private server-side metadata report path.')
    args=parser.parse_args()
    try:report=Account(args.username,os.environ.get('PA_API_TOKEN','')).preflight()
    except ValueError as error:print(str(error),file=sys.stderr);return 2
    text=json.dumps(report,indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        args.report.write_text(text+'\n');args.report.chmod(0o600)
    print(text);return 0

if __name__=='__main__':raise SystemExit(main())
