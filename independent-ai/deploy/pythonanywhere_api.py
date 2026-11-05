"""Scoped provider operations. Credentials travel only in a fixed-host header.

This module has no import-time network or filesystem side effects. Callers must
inspect existing provider state before mutations; no billing APIs are permitted.
"""
import json,os,re,secrets
from pathlib import PurePosixPath
from urllib.parse import urlencode,quote
from urllib.request import Request,build_opener
from urllib.error import HTTPError,URLError
try:
    from .pythonanywhere_preflight import Account,HOST,RefuseRedirects
except ImportError:
    from pythonanywhere_preflight import Account,HOST,RefuseRedirects

class ProviderError(Exception):
    def __init__(self,status=None):
        self.status=status
        super().__init__('Provider request returned HTTP '+str(status) if status else 'Provider request could not be completed securely.')

class Provider:
    def __init__(self,username=None,token=None,opener=None):
        self.username=username if username is not None else os.environ.get('PA_USERNAME','')
        self._token=token if token is not None else os.environ.get('PA_API_TOKEN','')
        Account(self.username,self._token)  # Validate without emitting values.
        self._opener=opener or build_opener(RefuseRedirects())
        self.base=f'https://{HOST}/api/v0/user/{self.username}/'
    def _resource_allowed(self,method,resource):
        if resource in ('consoles/','webapps/'):
            return method in ('GET','POST','OPTIONS')
        if re.fullmatch(r'consoles/[0-9]+/',resource):return method=='GET'
        domain=re.escape(self.username+'.pythonanywhere.com')
        if re.fullmatch(r'webapps/'+domain+r'/',resource):return method in ('GET','PATCH')
        if re.fullmatch(r'webapps/'+domain+r'/(enable|disable|reload)/',resource):return method=='POST'
        if re.fullmatch(r'webapps/'+domain+r'/(ssl|static_files)/',resource):return method=='GET'
        return False
    def _request(self,method,resource,body=None,content_type=None,raw=False,file_path=None):
        if file_path is None and not self._resource_allowed(method,resource):raise ValueError('Operation outside Haven provider scope.')
        if file_path is not None:
            if method not in ('GET','POST') or resource!='files/path'+quote(file_path,safe='/'):raise ValueError('Invalid provider file operation.')
        headers={'Authorization':'Token '+self._token,'Accept':'application/json'}
        if content_type:headers['Content-Type']=content_type
        try:
            with self._opener.open(Request(self.base+resource,data=body,headers=headers,method=method),timeout=35) as response:
                data=response.read(2_000_001)
                if len(data)>2_000_000:raise ProviderError()
                if raw:return data
                return json.loads(data) if data else None
        except HTTPError as error:raise ProviderError(error.code) from None
        except (URLError,TimeoutError,json.JSONDecodeError,UnicodeDecodeError):raise ProviderError() from None
    def request(self,method,resource,fields=None):
        body=urlencode(fields).encode() if fields is not None else None
        return self._request(method,resource,body,'application/x-www-form-urlencoded' if body is not None else None)
    def _file_path(self,path,write):
        root='/home/'+self.username
        path=str(path)
        if str(PurePosixPath(path))!=path or any(p in ('.','..') for p in path.split('/')) or not path.startswith('/'):
            raise ValueError('Provider file path must be normalized and absolute.')
        scopes=(root+'/haven-install/',root+'/haven/',root+'/haven-data/')
        wsgi='/var/www/'+self.username+'_pythonanywhere_com_wsgi.py'
        logs=tuple('/var/log/'+self.username+'.pythonanywhere.com.'+kind+'.log' for kind in ('error','server','access'))
        if not(path.startswith(scopes) or path==wsgi or (not write and path in logs)):raise ValueError('Provider file path outside Haven directories.')
        if write and path.startswith(root+'/haven-data/'):raise ValueError('Use the private bootstrap for owner data initialization.')
        return path
    def read_file(self,path):
        path=self._file_path(path,False)
        return self._request('GET','files/path'+quote(path,safe='/'),raw=True,file_path=path)
    def upload(self,path,content):
        path=self._file_path(path,True)
        if not isinstance(content,bytes) or len(content)>1_500_000:raise ValueError('Deployment upload exceeds the size limit.')
        boundary='HavenUpload'+secrets.token_hex(16)
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="content"; filename="deployment.bin"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+content+f'\r\n--{boundary}--\r\n'.encode()
        self._request('POST','files/path'+quote(path,safe='/'),body,'multipart/form-data; boundary='+boundary,raw=True,file_path=path)
