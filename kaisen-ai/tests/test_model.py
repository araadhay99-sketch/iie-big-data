import hashlib,json,unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from kaisen.model import install_model,load_manifest,ModelError,HTTPSRedirects
from kaisen.budget import Budget,BudgetError
from urllib.request import Request

DATA=b'GGUF'+b'synthetic-model-fixture'*100
def manifest(data=DATA):return {'filename':'synthetic.gguf','revision':'a'*40,'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data),'download_url':'https://huggingface.co/example/repo/resolve/'+('a'*40)+'/synthetic.gguf'}
class Response(BytesIO):
    def __init__(self,data):super().__init__(data);self.headers={'Content-Length':str(len(data))}
class FakeOpener:
    def __init__(self,data=DATA):self.data=data;self.requests=[]
    def open(self,request,timeout):self.requests.append(request);return Response(self.data)

class ModelInstallerTest(unittest.TestCase):
    def test_streamed_checksum_install_and_idempotency_without_second_download(self):
        with TemporaryDirectory() as tmp:
            opener=FakeOpener();result=install_model(tmp,manifest(),opener)
            self.assertTrue(result['checksum_verified'])
            self.assertEqual((Path(tmp)/'models/synthetic.gguf').read_bytes(),DATA)
            self.assertFalse(install_model(tmp,manifest(),opener)['downloaded_now'])
            self.assertEqual(len(opener.requests),1)
    def test_corrupt_download_never_becomes_installed_model(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ModelError):install_model(tmp,manifest(),FakeOpener(b'x'*len(DATA)))
            self.assertFalse((Path(tmp)/'models/synthetic.gguf').exists())
            self.assertFalse(list((Path(tmp)/'models').glob('*.part')))
    def test_budget_blocks_network_download_and_existing_file_is_preserved(self):
        with TemporaryDirectory() as tmp:
            opener=FakeOpener()
            with self.assertRaises(BudgetError):install_model(tmp,manifest(),opener,Budget(tmp,100))
            self.assertEqual(opener.requests,[])
            path=Path(tmp)/'models/synthetic.gguf';path.write_bytes(b'existing model')
            with self.assertRaises(ModelError):install_model(tmp,manifest(),opener)
            self.assertEqual(path.read_bytes(),b'existing model')
    def test_pins_and_redirects_are_validated(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'manifest.json';value=manifest();value['revision']='main';path.write_text(json.dumps(value))
            with self.assertRaises(ModelError):load_manifest(path)
        with self.assertRaises(ModelError):HTTPSRedirects().redirect_request(Request('https://huggingface.co/file'),None,302,'Found',{},'http://evil.example/file')
    def test_archive_and_model_install_share_the_managed_writer_lock(self):
        with TemporaryDirectory() as tmp:
            budget=Budget(tmp);opener=FakeOpener()
            with budget.writer():
                with self.assertRaises(BudgetError):install_model(tmp,manifest(),opener,budget)
            self.assertEqual(opener.requests,[])
            self.assertTrue(install_model(tmp,manifest(),opener,budget)['checksum_verified'])

if __name__=='__main__':unittest.main()
