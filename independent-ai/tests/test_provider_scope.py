import unittest
from io import BytesIO
from urllib.error import HTTPError
from deploy.pythonanywhere_api import Provider,ProviderError

class FakeOpener:
    def __init__(self):self.calls=[]
    def open(self,request,timeout):self.calls.append(request);return BytesIO(b'{}')

class ProviderScopeTest(unittest.TestCase):
    def setUp(self):self.opener=FakeOpener();self.api=Provider('example','synthetic-secret',self.opener)
    def test_forbids_unrelated_endpoints_and_owner_data_writes(self):
        for endpoint in ('billing/','always_on/','webapps/other.pythonanywhere.com/','../other/consoles/','https://evil.example/'):
            with self.assertRaises(ValueError):self.api.request('POST',endpoint,{})
        for path in ('/etc/passwd','/home/other/haven/a','/home/example/haven/../.bashrc','/home/example/haven-data/haven.sqlite3'):
            with self.assertRaises(ValueError):self.api.upload(path,b'example')
        self.assertEqual(self.opener.calls,[])
    def test_upload_is_scoped_to_fixed_https_host_and_multipart_field(self):
        self.api.upload('/home/example/haven-install/haven-source.zip',b'fictional-source')
        request=self.opener.calls[0]
        self.assertEqual(request.get_method(),'POST')
        self.assertEqual(request.full_url,'https://www.pythonanywhere.com/api/v0/user/example/files/path/home/example/haven-install/haven-source.zip')
        self.assertIn(b'name="content"',request.data)
        self.assertNotIn(b'synthetic-secret',request.data)
    def test_errors_never_echo_provider_response_bodies(self):
        class Broken:
            def open(self,request,timeout):raise HTTPError(request.full_url,403,'Forbidden',{},BytesIO(b'synthetic-secret'))
        with self.assertRaises(ProviderError) as caught:Provider('example','synthetic-secret',Broken()).request('GET','consoles/')
        self.assertEqual(caught.exception.status,403)
        self.assertNotIn('synthetic-secret',str(caught.exception))
    def test_only_this_sites_known_logs_can_be_read_and_never_written(self):
        self.assertEqual(self.api.read_file('/var/log/example.pythonanywhere.com.error.log'),b'{}')
        for path in ('/var/log/other.pythonanywhere.com.error.log','/var/log/example.pythonanywhere.com.unknown.log'):
            with self.assertRaises(ValueError):self.api.read_file(path)
        with self.assertRaises(ValueError):self.api.upload('/var/log/example.pythonanywhere.com.error.log',b'overwrite')

if __name__=='__main__':unittest.main()
