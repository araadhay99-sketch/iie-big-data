"""Optional hosting adapter test; requires requirements-hosting.txt."""
from tempfile import TemporaryDirectory
from pathlib import Path
import importlib.util,multiprocessing,os,unittest,httpx
from unittest.mock import patch
from app import Settings
from locking import WorkspaceLock

@unittest.skipUnless(importlib.util.find_spec('a2wsgi'),'Optional WSGI hosting adapter not installed')
class WSGICompatibilityTest(unittest.TestCase):
    def test_construction_and_unstarted_close_have_no_worker_resources(self):
        from wsgi import create_wsgi_application
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'workspace'
            with patch('wsgi.create_app') as build,patch('wsgi.asyncio.new_event_loop') as loop,patch('wsgi.threading.Thread.start') as start:
                application=create_wsgi_application(Settings(root))
                self.assertFalse(root.exists())
                application.close();application.close()
                build.assert_not_called();loop.assert_not_called();start.assert_not_called()

    @unittest.skipUnless(hasattr(os,'fork'),'Requires POSIX prefork hosting')
    def test_application_imported_before_fork_serves_first_request_in_child(self):
        from wsgi import create_wsgi_application
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'workspace'
            application=create_wsgi_application(Settings(root))
            parent,child=multiprocessing.get_context('fork').Pipe(duplex=False)
            def serve():
                try:
                    with httpx.Client(transport=httpx.WSGITransport(app=application),base_url='https://testserver') as client:
                        response=client.get('/api/session')
                        child.send((response.status_code,response.json(),application._pid==os.getpid(),application.thread.is_alive()))
                finally:
                    application.close();child.close()
            process=multiprocessing.get_context('fork').Process(target=serve)
            try:
                process.start();child.close()
                self.assertTrue(parent.poll(15),'Forked worker did not respond before the deadline.')
                status,body,owned,alive=parent.recv()
                self.assertEqual(status,200)
                self.assertEqual(body,{'authenticated':False,'setup_required':True,'cloud_only':True})
                self.assertTrue(owned);self.assertTrue(alive)
                process.join(5)
                self.assertEqual(process.exitcode,0)
                self.assertIsNone(application.api)
                with WorkspaceLock(root):pass
            finally:
                if process.is_alive():process.terminate();process.join(5)
                parent.close();application.close()

    def test_failed_gateway_initialization_releases_store_and_loop(self):
        import wsgi
        with TemporaryDirectory() as tmp:
            settings=Settings(Path(tmp))
            application=wsgi.create_wsgi_application(settings)
            created=[]
            def fail_gateway(api,**kwargs):
                created.append((api,kwargs['loop'],application.thread))
                raise RuntimeError('Synthetic gateway initialization failure.')
            try:
                with patch('wsgi.ASGIMiddleware',side_effect=fail_gateway):
                    with self.assertRaisesRegex(RuntimeError,'Synthetic gateway initialization failure.'):
                        application._initialize()
                api,loop,thread=created[0]
                self.assertTrue(api.state.store.lock.handle.closed)
                self.assertTrue(loop.is_closed());self.assertFalse(thread.is_alive())
                with WorkspaceLock(settings.data_dir):pass
                self.assertIsNone(application.gateway)
            finally:application.close()

    def test_failed_model_initialization_releases_store(self):
        from wsgi import create_wsgi_application
        with TemporaryDirectory() as tmp:
            settings=Settings(Path(tmp))
            application=create_wsgi_application(settings)
            try:
                with patch('app.LocalAssistant',side_effect=RuntimeError('Synthetic model initialization failure.')):
                    with self.assertRaisesRegex(RuntimeError,'Synthetic model initialization failure.'):
                        application._initialize()
                with WorkspaceLock(settings.data_dir):pass
            finally:application.close()

    def test_started_application_rejects_another_process_without_unlocking(self):
        from wsgi import create_wsgi_application
        with TemporaryDirectory() as tmp:
            settings=Settings(Path(tmp))
            application=create_wsgi_application(settings)
            try:
                application._initialize()
                with patch('wsgi.os.getpid',return_value=os.getpid()+1):
                    with self.assertRaisesRegex(RuntimeError,'cannot be reused in another process'):
                        application._initialize()
                    application.close()
                self.assertFalse(application.closed)
                self.assertTrue(application.thread.is_alive())
                with self.assertRaisesRegex(ValueError,'workspace is already open'):
                    WorkspaceLock(settings.data_dir)
            finally:application.close();application.close()

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
