"""Run with python3 -m unittest discover -s tests -v."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase,main
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from fastapi.testclient import TestClient
import sqlite3,json,hashlib
from app import create_app,Settings,COOKIE

PASSWORD='private-test-password-123'
HEADERS={'Origin':'http://testserver','Content-Type':'application/json'}

class HavenTest(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name)
        self.settings=Settings(self.root,quota_bytes=50000,max_file_bytes=30000,cloud_only=False)
        self.app=create_app(self.settings);self.client=TestClient(self.app)
    def tearDown(self):self.client.close();self.app.state.store.close();self.temp.cleanup()
    def setup_owner(self):
        r=self.client.post('/api/setup',json={'password':PASSWORD},headers=HEADERS)
        self.assertEqual(r.status_code,200,r.text)
    def upload(self,text='The launch code is ORCHID-728. Delivery is on Tuesday.',name='notes.txt'):
        return self.client.post('/api/files',files={'file':(name,text.encode(),'text/plain')},headers={'Origin':'http://testserver'})

    def test_auth_setup_cookie_and_no_plain_password(self):
        self.assertEqual(self.client.get('/api/session').json(),{'authenticated':False,'setup_required':True,'cloud_only':False})
        for route in ['/api/status','/api/files','/api/messages']:
            self.assertEqual(self.client.get(route).status_code,401)
        self.assertEqual(self.client.post('/api/setup',json={'password':'short'},headers=HEADERS).status_code,422)
        self.setup_owner()
        r=self.client.post('/api/setup',json={'password':PASSWORD},headers=HEADERS)
        self.assertEqual(r.status_code,409)
        with self.app.state.store.db() as db:saved=db.execute("SELECT value FROM settings WHERE key='password'").fetchone()[0]
        self.assertNotIn(PASSWORD,saved)
        r=self.client.post('/api/login',json={'password':PASSWORD},headers=HEADERS)
        cookie=r.headers['set-cookie'].lower()
        self.assertIn('httponly',cookie);self.assertIn('samesite=strict',cookie)

    def test_csrf_origin_host_and_form_posts_rejected(self):
        self.assertEqual(self.client.post('/api/setup',json={'password':PASSWORD}).status_code,403)
        self.assertEqual(self.client.post('/api/setup',json={'password':PASSWORD},headers={**HEADERS,'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.post('/api/setup',data={'password':PASSWORD},headers={'Origin':'http://testserver'}).status_code,415)
        self.assertEqual(self.client.get('/api/session',headers={'Host':'evil.example'}).status_code,400)

    def test_login_throttle_and_logout_revokes_session(self):
        self.setup_owner();self.client.post('/api/logout',json={},headers=HEADERS)
        for _ in range(5):self.assertEqual(self.client.post('/api/login',json={'password':'wrong'},headers=HEADERS).status_code,401)
        self.assertEqual(self.client.post('/api/login',json={'password':PASSWORD},headers=HEADERS).status_code,429)
        self.client.close();self.app.state.store.close();self.app=create_app(self.settings);self.client=TestClient(self.app)
        self.assertEqual(self.client.post('/api/login',json={'password':PASSWORD},headers=HEADERS).status_code,200)
        stolen=self.client.cookies.get(COOKIE)
        self.client.post('/api/logout',json={},headers=HEADERS)
        other=TestClient(self.app)
        try:
            other.cookies.set(COOKIE,stolen)
            self.assertEqual(other.get('/api/files').status_code,401)
        finally:other.close()

    def test_upload_download_name_sanitization_and_duplicate_names(self):
        self.setup_owner();r=self.upload(name='../../notes.txt');self.assertEqual(r.status_code,200,r.text)
        file=r.json();self.assertEqual(file['name'],'notes.txt');self.assertTrue(file['indexed'])
        r=self.client.get('/api/files/'+file['id']+'/download')
        self.assertEqual(r.content,b'The launch code is ORCHID-728. Delivery is on Tuesday.')
        self.assertIn('attachment',r.headers['content-disposition'])
        second=self.upload(name='notes.txt').json();self.assertNotEqual(file['id'],second['id'])
        self.assertEqual(len(self.client.get('/api/files').json()['files']),2)
        self.client.post('/api/logout',json={},headers=HEADERS)
        self.assertEqual(self.client.get('/api/files/'+file['id']+'/download').status_code,401)

    def test_answer_from_real_uploaded_file_without_network(self):
        self.setup_owner();file=self.upload().json()
        with patch('socket.socket.connect',side_effect=AssertionError('Network forbidden')):
            r=self.client.post('/api/chat',json={'message':'What is the launch code?'},headers=HEADERS)
            self.assertEqual(r.status_code,200,r.text)
            message=r.json()['message'];self.assertIn('ORCHID-728',message['content'])
            self.assertEqual(message['sources'][0]['id'],file['id'])
            self.assertEqual(self.client.get('/api/status').json()['assistant']['mode'],'local-knowledge')
        self.assertEqual(len(self.client.get('/api/messages').json()['messages']),2)

    def test_no_relevant_answer_is_not_invented(self):
        self.setup_owner();self.upload('The shipment uses a blue container and arrives on Tuesday.')
        r=self.client.post('/api/chat',json={'message':'Explain quantum entanglement and black holes'},headers=HEADERS)
        self.assertEqual(r.json()['message']['sources'],[])
        self.assertIn('couldn’t find',r.json()['message']['content'])

    def test_local_intent_model_identity(self):
        self.setup_owner()
        r=self.client.post('/api/chat',json={'message':'Who are you?'},headers=HEADERS)
        self.assertIn('intent classifier',r.json()['message']['content'])

    def test_trash_excludes_search_restore_and_purge_reclaims_quota(self):
        self.setup_owner();file=self.upload().json();id=file['id']
        self.assertEqual(self.client.post(f'/api/files/{id}/purge',json={'confirm':True},headers=HEADERS).status_code,409)
        self.client.post(f'/api/files/{id}/trash',json={},headers=HEADERS)
        self.assertEqual(self.client.get('/api/files').json()['files'],[])
        self.assertEqual(len(self.client.get('/api/files?trash=true').json()['files']),1)
        answer=self.client.post('/api/chat',json={'message':'What is the launch code?'},headers=HEADERS).json()['message']
        self.assertNotIn('ORCHID-728',answer['content'])
        self.client.post(f'/api/files/{id}/restore',json={},headers=HEADERS)
        self.assertEqual(len(self.client.get('/api/files').json()['files']),1)
        self.client.post(f'/api/files/{id}/trash',json={},headers=HEADERS)
        self.assertEqual(self.client.post(f'/api/files/{id}/purge',json={'confirm':False},headers=HEADERS).status_code,422)
        self.assertEqual(self.client.post(f'/api/files/{id}/purge',json={'confirm':True},headers=HEADERS).status_code,200)
        self.assertEqual(self.client.get('/api/status').json()['storage']['used_bytes'],0)
        self.assertFalse((self.root/'blobs'/id).exists())
        with self.app.state.store.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM passages').fetchone()[0],0)

    def test_oversized_and_quota_failures_leave_no_orphans(self):
        self.setup_owner()
        self.assertEqual(self.upload('x'*30001).status_code,413)
        self.assertEqual(list((self.root/'blobs').iterdir()),[])
        self.assertEqual(self.upload('x'*26000).status_code,200)
        self.assertEqual(self.upload('y'*26000).status_code,413)
        self.assertEqual(len(list((self.root/'blobs').iterdir())),1)
        self.assertEqual(self.client.get('/api/status').json()['storage']['used_bytes'],26000)

    def test_binary_stored_not_indexed_and_literal_markup_is_preserved(self):
        self.setup_owner()
        r=self.client.post('/api/files',files={'file':('scan.pdf',b'%PDF\x00\xff')},headers={'Origin':'http://testserver'})
        self.assertFalse(r.json()['indexed'])
        r=self.upload('<script>alert(1)</script> alpha code = WATER-111.','<img onerror=alert(1)>.md')
        self.assertEqual(r.status_code,200)
        self.assertIn('<img',r.json()['name'])
        answer=self.client.post('/api/chat',json={'message':'alpha code'},headers=HEADERS).json()['message']
        self.assertIn('WATER-111',answer['content'])

    def test_restart_preserves_owner_files_and_history(self):
        self.setup_owner();id=self.upload().json()['id']
        self.client.post('/api/chat',json={'message':'launch code'},headers=HEADERS)
        self.client.close();self.app.state.store.close();self.app=create_app(self.settings);self.client=TestClient(self.app)
        self.assertFalse(self.client.get('/api/session').json()['setup_required'])
        self.client.post('/api/login',json={'password':PASSWORD},headers=HEADERS)
        self.assertEqual(self.client.get('/api/files').json()['files'][0]['id'],id)
        self.assertEqual(len(self.client.get('/api/messages').json()['messages']),2)

    def test_interrupted_purge_recovery(self):
        self.setup_owner();id=self.upload().json()['id'];self.client.close();self.app.state.store.close()
        blob=self.root/'blobs'/id;pending=blob.with_name(id+'.purging');blob.replace(pending)
        self.app=create_app(self.settings);self.client=TestClient(self.app)
        self.assertTrue(blob.exists());self.assertFalse(pending.exists())

    def test_external_model_endpoints_rejected(self):
        for url in ['https://api.external.example','http://127.0.0.1.evil.example','http://user:secret@localhost:1234','ftp://localhost']:
            with self.assertRaises(ValueError):create_app(Settings(self.root/'other',ollama_url=url))

    def test_upload_requires_auth_before_multipart_parsing_and_caps_body(self):
        r=self.client.post('/api/files',content=b'not-even-a-valid-multipart-body',headers={'Origin':'http://testserver','Content-Type':'multipart/form-data; boundary=wrong'})
        self.assertEqual(r.status_code,401)
        self.setup_owner()
        r=self.client.post('/api/files',content=b'x'*100000,headers={'Origin':'http://testserver','Content-Type':'multipart/form-data; boundary=wrong'})
        self.assertEqual(r.status_code,413)
        self.assertEqual(list((self.root/'blobs').iterdir()),[])

    def test_chunked_body_limits_are_enforced_without_content_length(self):
        self.setup_owner()
        def chunks():
            yield b'{"message":"'
            yield b'x'*21000
            yield b'"}'
        r=self.client.post('/api/chat',content=chunks(),headers=HEADERS)
        self.assertEqual(r.status_code,413,r.text)

    def test_workspace_lock_and_interrupted_upload_cleanup(self):
        self.setup_owner();id=self.upload().json()['id']
        with self.assertRaises(ValueError):create_app(self.settings)
        incomplete=self.root/'blobs'/('a'*32+'.part');incomplete.write_bytes(b'partial')
        orphan=self.root/'blobs'/('b'*32);orphan.write_bytes(b'untracked')
        arbitrary=self.root/'blobs'/'keep-me.txt';arbitrary.write_text('Not an application-generated filename.')
        self.client.close();self.app.state.store.close();self.app=create_app(self.settings);self.client=TestClient(self.app)
        self.assertFalse(incomplete.exists());self.assertFalse(orphan.exists());self.assertTrue(arbitrary.exists());self.assertTrue((self.root/'blobs'/id).exists())

    def test_successful_clear_cannot_be_undone_by_inflight_chat(self):
        self.setup_owner();started=Event();release=Event()
        def slow_answer(*args):started.set();release.wait(3);return 'Previously started answer',[]
        with patch('assistant.LocalAssistant.respond',side_effect=slow_answer),ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(self.client.post,'/api/chat',json={'message':'hello'},headers=HEADERS)
            try:
                self.assertTrue(started.wait(2))
                self.assertEqual(self.client.post('/api/messages/clear',json={},headers=HEADERS).status_code,409)
            finally:release.set()
            self.assertEqual(future.result().status_code,200)
        self.assertEqual(self.client.post('/api/messages/clear',json={},headers=HEADERS).status_code,200)
        self.assertEqual(self.client.get('/api/messages').json()['messages'],[])

    def test_backup_restore_preserves_data_revokes_sessions_and_checks_paths(self):
        from backup import backup,restore
        import zipfile
        self.setup_owner();id=self.upload().json()['id'];token=self.client.cookies.get(COOKIE)
        archive=self.root.parent/(self.root.name+'-backup.zip')
        restored=self.root/'restored'
        try:
            with self.assertRaises(ValueError):backup(self.root,archive)
            self.client.close();self.app.state.store.close()
            self.assertEqual(backup(self.root,archive),1);restore(archive,restored)
            with self.assertRaises(ValueError):restore(archive,restored)
            restored_app=create_app(Settings(restored,cloud_only=False))
            client=TestClient(restored_app)
            try:
                client.cookies.set(COOKIE,token);self.assertEqual(client.get('/api/files').status_code,401)
                self.assertEqual(client.post('/api/login',json={'password':PASSWORD},headers=HEADERS).status_code,200)
                self.assertEqual(client.get('/api/files').json()['files'][0]['id'],id)
            finally:client.close();restored_app.state.store.close()
            with zipfile.ZipFile(archive,'a') as z:z.writestr('../escape.txt','not allowed')
            with self.assertRaises(ValueError):restore(archive,self.root/'bad-restore')
        finally:archive.unlink(missing_ok=True)

    def test_cloud_mode_has_memory_token_no_cookie_and_no_download(self):
        self.client.close();self.app.state.store.close()
        self.app=create_app(Settings(self.root,cloud_only=True));self.client=TestClient(self.app)
        response=self.client.post('/api/setup',json={'password':PASSWORD},headers=HEADERS)
        self.assertEqual(response.status_code,200)
        self.assertNotIn('set-cookie',response.headers)
        self.assertEqual(dict(self.client.cookies),{})
        token=response.json()['token'];auth={'Authorization':'Bearer '+token}
        self.assertEqual(self.client.get('/api/status').status_code,401)
        r=self.client.get('/api/status',headers=auth)
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['client'],{'cloud_only':True,'downloads_enabled':False,'session_storage':'memory'})
        r=self.client.post('/api/files',files={'file':('cloud-note.txt',b'The satellite marker is SERVER-612.')},headers={'Origin':'http://testserver',**auth})
        self.assertEqual(r.status_code,200,r.text);id=r.json()['id']
        self.assertEqual(self.client.get('/api/files/'+id+'/download',headers=auth).status_code,403)
        answer=self.client.post('/api/chat',json={'message':'What is the satellite marker?'},headers={**HEADERS,**auth})
        self.assertIn('SERVER-612',answer.json()['message']['content'])
        self.client.cookies.set(COOKIE,token)
        self.assertEqual(self.client.get('/api/status').status_code,401,'A cookie must not authorize cloud-only mode.')
        self.client.post('/api/logout',json={},headers={**HEADERS,**auth})
        self.assertEqual(self.client.get('/api/status',headers=auth).status_code,401)

if __name__=='__main__':main()
