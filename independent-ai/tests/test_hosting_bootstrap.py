import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
from tempfile import TemporaryDirectory
import unittest
import warnings
import zipfile

from deploy.pythonanywhere_bootstrap import (
    InstallError, REQUIRED_FILES, extract_source, provision_owner, verify_archive, write_status,
)


class HostingBootstrapTest(unittest.TestCase):
    def bundle(self, directory, extra=(), replace=None):
        path = Path(directory) / 'source.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for name in sorted(REQUIRED_FILES):
                archive.writestr(name, (replace or {}).get(name, 'synthetic runtime ' + name))
            for name, data in extra:
                archive.writestr(name, data)
        return path

    def test_checksum_and_identical_reextraction_preserve_files(self):
        with TemporaryDirectory() as temporary:
            archive = self.bundle(temporary)
            checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
            verify_archive(archive, checksum)
            destination = Path(temporary) / 'haven'
            extract_source(archive, destination)
            extract_source(archive, destination)
            self.assertEqual((destination / 'app.py').read_text(), 'synthetic runtime app.py')
            with self.assertRaises(InstallError):
                verify_archive(archive, '0' * 64)
            (destination / 'app.py').write_text('existing owner change')
            with self.assertRaises(InstallError):
                extract_source(archive, destination)
            self.assertEqual((destination / 'app.py').read_text(), 'existing owner change')

    def test_paths_links_duplicates_and_unexpected_files_are_rejected_before_writes(self):
        for name in ('../outside', '/tmp/outside', 'static/../../outside', 'static//outside',
                     'static/./outside', 'static\\outside', 'credentials.json', 'static/C:drive'):
            with self.subTest(name=name), TemporaryDirectory() as temporary:
                archive = self.bundle(temporary, [(name, 'untrusted')])
                destination = Path(temporary) / 'haven'
                with self.assertRaises(InstallError):
                    extract_source(archive, destination)
                self.assertFalse(destination.exists())
        with TemporaryDirectory() as temporary:
            archive = self.bundle(temporary)
            with zipfile.ZipFile(archive, 'a') as output:
                item = zipfile.ZipInfo('static/link')
                item.create_system = 3
                item.external_attr = (stat.S_IFLNK | 0o777) << 16
                output.writestr(item, '/tmp/outside')
            with self.assertRaises(InstallError):
                extract_source(archive, Path(temporary) / 'haven')
        with TemporaryDirectory() as temporary:
            archive = self.bundle(temporary)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(archive, 'a') as output:
                    output.writestr('app.py', 'duplicate replacement')
            with self.assertRaises(InstallError):
                extract_source(archive, Path(temporary) / 'haven')

    def test_existing_destination_symlinks_are_not_followed(self):
        with TemporaryDirectory() as temporary:
            archive = self.bundle(temporary)
            destination = Path(temporary) / 'haven'
            destination.mkdir()
            outside = Path(temporary) / 'outside'
            outside.mkdir()
            (destination / 'static').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(InstallError):
                extract_source(archive, destination)
            self.assertFalse(list(outside.iterdir()))

    def test_owner_password_is_hashed_and_existing_owner_is_preserved(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / 'data'
            synthetic = 'synthetic-owner-password-9356'
            inputs = iter([synthetic, synthetic])
            self.assertEqual(provision_owner(root, lambda _prompt: next(inputs), lambda: True), 'created')
            with sqlite3.connect(root / 'haven.sqlite3') as database:
                saved = database.execute("SELECT value FROM settings WHERE key='password'").fetchone()[0]
            self.assertNotIn(synthetic, saved)
            value = json.loads(saved)
            self.assertEqual(value['hash'], hashlib.pbkdf2_hmac('sha256', synthetic.encode(), bytes.fromhex(value['salt']), 310000).hex())
            self.assertEqual(os.stat(root / 'haven.sqlite3').st_mode & 0o777, 0o600)
            def must_not_prompt(_prompt):
                self.fail('Existing owner must never be prompted or overwritten')
            self.assertEqual(provision_owner(root, must_not_prompt, lambda: False), 'preserved')
            with sqlite3.connect(root / 'haven.sqlite3') as database:
                self.assertEqual(database.execute("SELECT value FROM settings WHERE key='password'").fetchone()[0], saved)

    def test_password_validation_and_terminal_requirement_do_not_save_owner(self):
        cases = [('short', 'short'), ('x' * 257, 'x' * 257),
                 ('synthetic-password-one', 'synthetic-password-two')]
        for values in cases:
            with self.subTest(length=len(values[0])), TemporaryDirectory() as temporary:
                inputs = iter(values)
                with self.assertRaises(InstallError):
                    provision_owner(temporary, lambda _prompt: next(inputs), lambda: True)
                with sqlite3.connect(Path(temporary) / 'haven.sqlite3') as database:
                    self.assertIsNone(database.execute("SELECT value FROM settings WHERE key='password'").fetchone())
        with TemporaryDirectory() as temporary:
            with self.assertRaises(InstallError) as caught:
                provision_owner(temporary, lambda _prompt: self.fail('No terminal means no prompt'), lambda: False)
            self.assertEqual(caught.exception.code, 'OWNER_TERMINAL_REQUIRED')

    def test_status_is_atomic_private_metadata(self):
        with TemporaryDirectory() as temporary:
            write_status(Path(temporary), 'running_smoke_tests', public_webapp_created=False)
            path = Path(temporary) / 'status.json'
            self.assertEqual(json.loads(path.read_text())['phase'], 'running_smoke_tests')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual([p.name for p in Path(temporary).iterdir()], ['status.json'])


if __name__ == '__main__':
    unittest.main()
