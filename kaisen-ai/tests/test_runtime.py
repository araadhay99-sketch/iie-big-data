import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import tarfile
from tempfile import TemporaryDirectory
import unittest

from kaisen.budget import Budget, BudgetError
from scripts.install_runtime import archive_members, install_runtime, load_manifest, RuntimeError


def archive_bytes(entries):
    output = BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as archive:
        for name, kind, content in entries:
            member = tarfile.TarInfo(name); member.mode = 0o755
            if kind == 'file':
                member.size = len(content); archive.addfile(member, BytesIO(content))
            else:
                member.type = {'symlink': tarfile.SYMTYPE, 'hardlink': tarfile.LNKTYPE, 'fifo': tarfile.FIFOTYPE}[kind]
                member.linkname = content; archive.addfile(member)
    return output.getvalue()


class Response(BytesIO):
    def __init__(self, data):
        super().__init__(data); self.headers = {'Content-Length': str(len(data))}


class Opener:
    def __init__(self, data): self.data, self.calls = data, 0
    def open(self, request, timeout): self.calls += 1; return Response(self.data)


def metadata(data):
    return {'tag': 'b1', 'revision': 'a' * 40, 'filename': 'llama-b1-bin-ubuntu-x64.tar.gz',
            'download_url': 'https://github.com/ggml-org/llama.cpp/releases/download/b1/llama-b1-bin-ubuntu-x64.tar.gz',
            'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def smoke(command, **options):
    assert options['timeout'] == 30
    output = 'version b1' if command[-1] == '--version' else '--jinja --parallel --ctx-size --threads --n-predict --host'
    return subprocess.CompletedProcess(command, 0, output, '')


class RuntimeInstallerTest(unittest.TestCase):
    def test_safe_archive_installs_with_contained_links_and_records_smoke_only(self):
        data = archive_bytes([('bin/llama-server', 'file', b'fixture'), ('bin/lib.so.1', 'file', b'library'),
                              ('bin/lib.so', 'symlink', 'lib.so.1')])
        with TemporaryDirectory() as tmp:
            record = install_runtime(tmp, metadata(data), Opener(data), runner=smoke)
            self.assertTrue(record['checksum_verified']); self.assertFalse(record['inference_verified'])
            self.assertEqual((Path(tmp) / record['server_path']).read_bytes(), b'fixture')
            self.assertEqual(json.loads((Path(tmp) / 'runtime/installed.json').read_text()), record)
            self.assertEqual(list((Path(tmp) / 'runtime').glob('.install-*')), [])

    def test_unsafe_paths_links_and_special_files_never_run(self):
        for entry in [('../escape', 'file', b'x'), ('/absolute', 'file', b'x'),
                      ('bin/link', 'symlink', '../../escape'), ('bin/link', 'hardlink', '../escape'),
                      ('fifo', 'fifo', ''), ('bin/llama-server', 'symlink', '/bin/sh')]:
            with self.subTest(entry=entry), TemporaryDirectory() as tmp:
                data = archive_bytes([entry]); calls = []
                with self.assertRaises((RuntimeError, tarfile.FilterError)):
                    install_runtime(tmp, metadata(data), Opener(data), runner=lambda *a, **kw: calls.append(a))
                self.assertEqual(calls, []); self.assertFalse((Path(tmp) / 'runtime/b1').exists())

    def test_duplicate_member_and_expansion_member_limits(self):
        for entries, limits in [([('same', 'file', b'x')] * 2, {}),
                                ([('one', 'file', b'x'), ('two', 'file', b'y')], {'max_members': 1}),
                                ([('large', 'file', b'123')], {'max_bytes': 2})]:
            with self.subTest(limits=limits), TemporaryDirectory() as tmp:
                with tarfile.open(fileobj=BytesIO(archive_bytes(entries)), mode='r:gz') as archive:
                    with self.assertRaises(RuntimeError): archive_members(archive, Path(tmp), Budget(tmp), **limits)

    def test_checksum_budget_and_existing_files_block_execution_or_network(self):
        data = archive_bytes([('llama-server', 'file', b'x')])
        with TemporaryDirectory() as tmp:
            opener = Opener(data)
            with self.assertRaises(BudgetError): install_runtime(tmp, metadata(data), opener, Budget(tmp, 100), smoke)
            self.assertEqual(opener.calls, 0)
            target = Path(tmp) / 'runtime/b1'; target.mkdir(); (target / 'keep').write_text('preserved')
            with self.assertRaises(RuntimeError): install_runtime(tmp, metadata(data), opener, runner=smoke)
            self.assertEqual((target / 'keep').read_text(), 'preserved'); self.assertEqual(opener.calls, 0)
        with TemporaryDirectory() as tmp:
            manifest = metadata(data); manifest['sha256'] = '0' * 64
            with self.assertRaises(RuntimeError): install_runtime(tmp, manifest, Opener(data), runner=smoke)
            self.assertFalse((Path(tmp) / 'runtime/b1').exists())

    def test_smoke_failure_preserves_no_install_and_manifest_blocks_unpinned_url(self):
        data = archive_bytes([('llama-server', 'file', b'x')])
        def fail(*args, **kwargs): raise subprocess.TimeoutExpired('fixture', 30)
        with TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError): install_runtime(tmp, metadata(data), Opener(data), runner=fail)
            self.assertFalse((Path(tmp) / 'runtime/b1').exists())
            manifest = metadata(data); manifest['download_url'] = 'http://example.org/binary'
            path = Path(tmp) / 'manifest.json'; path.write_text(json.dumps(manifest))
            with self.assertRaises(RuntimeError): load_manifest(path)

    def test_runtime_writes_share_budget_lock_and_reject_symlink_install_paths(self):
        data = archive_bytes([('llama-server', 'file', b'x')])
        with TemporaryDirectory() as tmp, TemporaryDirectory() as outside:
            budget = Budget(tmp); opener = Opener(data)
            with budget.writer():
                with self.assertRaises(BudgetError): install_runtime(tmp, metadata(data), opener, budget, smoke)
            (Path(tmp) / 'runtime').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError): install_runtime(tmp, metadata(data), opener, budget, smoke)
            self.assertEqual(opener.calls, 0)


if __name__ == '__main__': unittest.main()
