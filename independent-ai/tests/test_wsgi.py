"""Optional hosting adapter test; requires requirements-hosting.txt."""
from tempfile import TemporaryDirectory
from pathlib import Path
import importlib.util,unittest,httpx
from app import Settings

@unittest.skipUnless(importlib.util.find_spec('a2wsgi'),'Optional WSGI hosting adapter not installed')
class WSGICompatibilityTest(unittest.TestCase):
    def test_cloud_auth_upload_answer_and_reload_over_wsgi(self):
        from wsgi import create_wsgi_application
        with TemporaryDirectory() as tmp:
            settings=Settings(Path(tmp),allowed_hosts=('haven.example',),cloud_only=True,quota_bytes=64*1024*1024)
            application=create_wsgi_application(settings)
            client=httpx.Client(transport=httpx.WSGITransport(app=application),base_url='https://haven.example')
            headers={'Origin':'https://haven.example'}
            try:
                self.assertEqual(client.get('/').status_code,200)
                self.assertIn('no-store',client.get('/static/app.js').headers['cache-control'])
                result=client.post('/api/setup',json={'password':'synthetic-host-password-456'},headers=headers)
                self.assertEqual(result.status_code,200,result.text)
                self.assertNotIn('set-cookie',result.headers)
                auth={**headers,'Authorization':'Bearer '+result.json()['token']}
                result=client.post('/api/files',files={'file':('server-note.md',b'The private observatory key is WSGI-864.')},headers=auth)
                self.assertEqual(result.status_code,200,result.text)
                file_id=result.json()['id']
                reply=client.post('/api/chat',json={'message':'What is the private observatory key?'},headers=auth)
                self.assertEqual(reply.status_code,200,reply.text)
                self.assertIn('WSGI-864',reply.json()['message']['content'])
                self.assertEqual(client.get('/api/files/'+file_id+'/download',headers=auth).status_code,403)
                self.assertEqual(client.get('/api/files').status_code,401)
            finally:client.close();application.close()

if __name__=='__main__':unittest.main()
