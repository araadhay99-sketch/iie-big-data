import unittest,json
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import Request
from deploy.pythonanywhere_preflight import Account,HOST,RefuseRedirects

class FakeOpener:
    def __init__(self):self.calls=[]
    def open(self,request,timeout):
        self.calls.append(request)
        data={'daily_cpu_limit_seconds':100,'internal_secret':'not-for-report'} if request.full_url.endswith('/cpu/') else [{'domain_name':'example.pythonanywhere.com','password_protection_password':'private-value','source_directory':'/home/example/project'}]
        return BytesIO(json.dumps(data).encode())

class HostingPreflightTest(unittest.TestCase):
    def test_only_scoped_read_requests_and_safe_metadata_are_reported(self):
        opener=FakeOpener();account=Account('example_user','synthetic-test-token',opener)
        report=account.preflight();encoded=json.dumps(report)
        self.assertNotIn('synthetic-test-token',encoded);self.assertNotIn('private-value',encoded);self.assertNotIn('internal_secret',encoded)
        self.assertEqual(len(opener.calls),2)
        for request in opener.calls:
            self.assertEqual(request.get_method(),'GET')
            self.assertTrue(request.full_url.startswith('https://'+HOST+'/api/v0/user/example_user/'))
        with self.assertRaises(ValueError):account.read('billing')
    def test_username_cannot_change_host_or_request_path(self):
        for name in ['../other','example/other','name?token=secret','https://evil.example','']:
            with self.assertRaises(ValueError):Account(name,'synthetic-test-token')
    def test_provider_errors_do_not_echo_secret_response_bodies(self):
        class Broken:
            def open(self,request,timeout):raise HTTPError(request.full_url,403,'Forbidden',{},BytesIO(b'synthetic-test-token'))
        with self.assertRaises(ValueError) as caught:Account('example','synthetic-test-token',Broken()).preflight()
        self.assertNotIn('synthetic-test-token',str(caught.exception));self.assertIn('403',str(caught.exception))
    def test_redirects_are_never_followed_with_account_credentials(self):
        request=Request('https://'+HOST+'/api/v0/user/example/cpu/')
        with self.assertRaises(HTTPError):RefuseRedirects().redirect_request(request,None,302,'Found',{},'https://evil.example')

if __name__=='__main__':unittest.main()
