import hashlib,json,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from kaisen.server import server_command
from kaisen.model import ModelError

class ServerPreparationTest(unittest.TestCase):
    def fixture(self,tmp):
        root=Path(tmp);(root/'models').mkdir();(root/'runtime').mkdir()
        data=b'GGUF synthetic fixture';(root/'models/example.gguf').write_bytes(data)
        (root/'runtime/llama-server').write_text('synthetic executable fixture; never executed')
        (root/'runtime/installed.json').write_text(json.dumps({'server_path':'runtime/llama-server','checksum_verified':True,'runtime_smoke_verified':True}))
        return root,{'filename':'example.gguf','size_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    def test_refuses_missing_or_modified_weights(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ModelError):server_command(tmp,{'filename':'missing.gguf'})
            root,manifest=self.fixture(tmp);(root/'models/example.gguf').write_bytes(b'corrupted')
            with self.assertRaises(ModelError):server_command(root,manifest)
    def test_loopback_and_resource_flags_are_explicit(self):
        with TemporaryDirectory() as tmp:
            root,manifest=self.fixture(tmp);command=server_command(root,manifest)
            self.assertEqual(command[command.index('--host')+1],'127.0.0.1')
            self.assertEqual(command[command.index('--parallel')+1],'1')
            self.assertEqual(command[command.index('--ctx-size')+1],'8192')
            self.assertEqual(command[command.index('--n-predict')+1],'2048')
    def test_runtime_record_cannot_escape_project(self):
        with TemporaryDirectory() as tmp:
            root,manifest=self.fixture(tmp)
            (root/'runtime/installed.json').write_text(json.dumps({'server_path':'../external','checksum_verified':True,'runtime_smoke_verified':True}))
            with self.assertRaises(ValueError):server_command(root,manifest)

if __name__=='__main__':unittest.main()
