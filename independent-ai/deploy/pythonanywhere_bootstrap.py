"""Private, interactive Haven installation; never creates a public web application.

Run on the hosting account with Python >=3.11. The operator supplies only the
archive checksum. The owner supplies their password privately at the terminal.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import getpass
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import sqlite3
import stat
import subprocess
import sys
import tempfile
import warnings
import zipfile

RUNTIME_FILES = frozenset({
    'app.py', 'assistant.py', 'locking.py', 'backup.py', 'wsgi.py',
    'requirements.txt', 'requirements-hosting.txt',
})
REQUIRED_FILES = RUNTIME_FILES | {'static/index.html', 'static/styles.css', 'static/app.js'}
HOME_LIMIT = 400 * 1024 * 1024
ARCHIVE_LIMIT = 8 * 1024 * 1024
PASSWORD_ITERATIONS = 310000


class InstallError(Exception):
    """Only fixed, non-sensitive messages are passed to this exception."""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def private_directory(path):
    path = Path(path)
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise InstallError('UNSAFE_DIRECTORY', 'A required private directory is not a regular directory.')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def write_status(directory, phase, **fields):
    private_directory(directory)
    payload = {'phase': phase, 'updated_at': datetime.now(timezone.utc).isoformat(), **fields}
    descriptor, temporary = tempfile.mkstemp(prefix='.status-', dir=directory)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            json.dump(payload, output, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, Path(directory) / 'status.json')
        (Path(directory) / 'status.json').chmod(0o600)
    finally:
        Path(temporary).unlink(missing_ok=True)


def verify_archive(archive, expected_sha256):
    archive = Path(archive)
    if not re.fullmatch(r'[0-9a-fA-F]{64}', expected_sha256 or ''):
        raise InstallError('INVALID_CHECKSUM', 'The supplied archive checksum is invalid.')
    if archive.is_symlink() or not archive.is_file():
        raise InstallError('MISSING_ARCHIVE', 'The source archive is missing or is not a regular file.')
    digest = hashlib.sha256()
    with archive.open('rb') as source:
        for chunk in iter(lambda: source.read(65536), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha256.lower():
        raise InstallError('CHECKSUM_MISMATCH', 'The source archive did not match its expected checksum.')


def extract_source(archive, destination):
    """Validate every member and collision before creating any runtime file."""
    destination = Path(destination)
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise InstallError('UNSAFE_DIRECTORY', 'The source destination is not a regular directory.')
    try:
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            if len(members) > 256 or sum(item.file_size for item in members) > ARCHIVE_LIMIT:
                raise InstallError('ARCHIVE_TOO_LARGE', 'The source archive exceeds its bounded installation size.')
            seen = set()
            files = []
            for item in members:
                raw = item.filename
                name = raw[:-1] if item.is_dir() else raw
                parts = name.split('/')
                if (not name or '\\' in raw or '\x00' in raw or ':' in raw
                        or PurePosixPath(name).is_absolute()
                        or any(part in ('', '.', '..') for part in parts)):
                    raise InstallError('UNSAFE_ARCHIVE', 'The source archive contains an unsafe path.')
                if name in seen:
                    raise InstallError('UNSAFE_ARCHIVE', 'The source archive contains duplicate paths.')
                seen.add(name)
                mode = item.external_attr >> 16
                file_kind = stat.S_IFMT(mode)
                if item.flag_bits & 1 or file_kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise InstallError('UNSAFE_ARCHIVE', 'The source archive contains a link or unsupported member.')
                if (file_kind == stat.S_IFDIR and not item.is_dir()) or (file_kind == stat.S_IFREG and item.is_dir()):
                    raise InstallError('UNSAFE_ARCHIVE', 'The source archive contains inconsistent file metadata.')
                allowed = name in RUNTIME_FILES or (parts[0] == 'static' and (item.is_dir() or len(parts) > 1))
                if not allowed or (item.is_dir() and parts[0] != 'static'):
                    raise InstallError('UNSAFE_ARCHIVE', 'The source archive contains a file outside the runtime allowlist.')
                target = destination.joinpath(*parts)
                for parent in [target, *target.parents]:
                    if parent == destination.parent:
                        break
                    if parent.is_symlink():
                        raise InstallError('UNSAFE_DESTINATION', 'A source destination contains a symbolic link.')
                    if parent != target and parent.exists() and not parent.is_dir():
                        raise InstallError('SOURCE_CONFLICT', 'An existing source directory conflicts with the archive.')
                if item.is_dir():
                    if target.exists() and not target.is_dir():
                        raise InstallError('SOURCE_CONFLICT', 'An existing source path conflicts with the archive.')
                    continue
                data = bundle.read(item)
                if target.exists() and (not target.is_file() or target.read_bytes() != data):
                    raise InstallError('SOURCE_CONFLICT', 'An existing source file differs; no existing file was overwritten.')
                files.append((target, data))
            if not REQUIRED_FILES.issubset(seen):
                raise InstallError('INCOMPLETE_ARCHIVE', 'The source archive is missing a required runtime file.')
        private_directory(destination)
        for target, data in files:
            private_directory(target.parent)
            if target.exists():
                continue
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, 'wb') as output:
                output.write(data)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError):
        raise InstallError('INVALID_ARCHIVE', 'The source archive could not be safely read.') from None


def home_allocation(home):
    """Conservative logical file-byte estimate, not the provider's quota meter."""
    total = 0
    seen = set()
    def traversal_error(_error):
        raise InstallError('CAPACITY_CHECK_FAILED', 'The account file allocation could not be measured safely.')
    for directory, folders, names in os.walk(home, followlinks=False, onerror=traversal_error):
        folders[:] = [name for name in folders if not (Path(directory) / name).is_symlink()]
        for name in names:
            info = (Path(directory) / name).lstat()
            key = (info.st_dev, info.st_ino)
            if stat.S_ISREG(info.st_mode) and key not in seen:
                total += info.st_size
                seen.add(key)
    return total


def check_capacity(home):
    used = home_allocation(home)
    if used >= HOME_LIMIT:
        raise InstallError('CAPACITY_LIMIT', 'The estimated home allocation exceeds the 400 MiB installation limit; nothing was deleted.')
    return used


def child_environment():
    environment = os.environ.copy()
    environment.update({
        'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
        'NUMEXPR_NUM_THREADS': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONNOUSERSITE': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
        'PIP_NO_CACHE_DIR': '1',
    })
    return environment


def run_quiet(arguments, environment, failure_code, failure_message, timeout=600):
    try:
        result = subprocess.run(arguments, env=environment, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise InstallError(failure_code, failure_message) from None
    if result.returncode:
        raise InstallError(failure_code, failure_message)


def prepare_environment(home, source):
    environment = child_environment()
    virtualenv = Path(home) / 'haven-venv'
    if virtualenv.is_symlink():
        raise InstallError('VENV_CONFLICT', 'The environment destination is a symbolic link.')
    if virtualenv.exists() and not (virtualenv / 'pyvenv.cfg').is_file():
        raise InstallError('VENV_CONFLICT', 'The environment destination contains an unrecognized directory.')
    if virtualenv.exists() and 'include-system-site-packages = true' not in (virtualenv / 'pyvenv.cfg').read_text().lower():
        raise InstallError('VENV_CONFLICT', 'The existing environment does not use the required system-package configuration.')
    if not virtualenv.exists():
        run_quiet([sys.executable, '-m', 'venv', '--system-site-packages', str(virtualenv)], environment,
                  'VENV_FAILED', 'The private Python environment could not be created.')
    python = virtualenv / 'bin' / 'python'
    if not python.exists():
        raise InstallError('VENV_FAILED', 'The private Python environment is incomplete.')
    run_quiet([str(python), '-m', 'pip', 'install', '--only-binary=:all:', '--no-cache-dir',
               '--no-compile', '-r', str(Path(source) / 'requirements-hosting.txt')], environment,
              'DEPENDENCY_INSTALL_FAILED', 'Pinned dependency installation failed; no public application was enabled.')
    return python, environment


def smoke_test(source, data):
    """Run under the new virtualenv against a temporary server-side workspace."""
    sys.path.insert(0, str(source))
    from app import Settings
    from wsgi import create_wsgi_application
    from wsgiref.util import setup_testing_defaults

    settings = Settings(Path(data), allowed_hosts=('haven.invalid',), cloud_only=True,
                        quota_bytes=64 * 1024 * 1024)

    def request(application, method, path, payload=None, token='', multipart=False):
        body = payload if multipart else (json.dumps(payload).encode() if payload is not None else b'')
        environment = {}
        setup_testing_defaults(environment)
        environment.update({'REQUEST_METHOD': method, 'PATH_INFO': path, 'QUERY_STRING': '',
                            'SERVER_NAME': 'haven.invalid', 'SERVER_PORT': '443',
                            'HTTP_HOST': 'haven.invalid', 'HTTP_ORIGIN': 'https://haven.invalid',
                            'wsgi.url_scheme': 'https', 'wsgi.input': BytesIO(body),
                            'CONTENT_LENGTH': str(len(body)),
                            'CONTENT_TYPE': 'multipart/form-data; boundary=haven-smoke' if multipart else 'application/json'})
        if token:
            environment['HTTP_AUTHORIZATION'] = 'Bearer ' + token
        received = {}
        def start_response(status, headers, _exc_info=None):
            received['status'] = int(status.split()[0])
            received['headers'] = dict((key.lower(), value) for key, value in headers)
        response = application(environment, start_response)
        try:
            content = b''.join(response)
        finally:
            if hasattr(response, 'close'):
                response.close()
        return received['status'], received['headers'], content

    password = 'synthetic-smoke-password-8642'
    marker = b'The observatory reference is HAVEN-HOST-8642.'
    application = create_wsgi_application(settings)
    try:
        assert request(application, 'GET', '/')[0] == 200
        assert request(application, 'GET', '/api/files')[0] == 401
        code, headers, body = request(application, 'POST', '/api/setup', {'password': password})
        assert code == 200 and 'set-cookie' not in headers
        code, _headers, body = request(application, 'POST', '/api/login', {'password': password})
        assert code == 200
        token = json.loads(body)['token']
        upload = (b'--haven-smoke\r\nContent-Disposition: form-data; name="file"; filename="observatory.md"\r\n'
                  b'Content-Type: text/markdown\r\n\r\n' + marker + b'\r\n--haven-smoke--\r\n')
        code, _headers, body = request(application, 'POST', '/api/files', upload, token, multipart=True)
        assert code == 200
        file_id = json.loads(body)['id']
        code, _headers, body = request(application, 'POST', '/api/chat', {'message': 'What is the observatory reference?'}, token)
        assert code == 200 and b'HAVEN-HOST-8642' in body
        assert request(application, 'GET', '/api/files/' + file_id + '/download', token=token)[0] == 403
    finally:
        application.close()
    application = create_wsgi_application(settings)
    try:
        code, _headers, body = request(application, 'POST', '/api/login', {'password': password})
        assert code == 200
        token = json.loads(body)['token']
        code, _headers, body = request(application, 'GET', '/api/files', token=token)
        assert code == 200 and any(item['id'] == file_id for item in json.loads(body)['files'])
        code, _headers, body = request(application, 'GET', '/api/messages', token=token)
        assert code == 200 and b'HAVEN-HOST-8642' in body
    finally:
        application.close()


@contextmanager
def owner_database(data_directory):
    import fcntl
    data_directory = private_directory(data_directory)
    database = data_directory / 'haven.sqlite3'
    lock_path = data_directory / 'server.lock'
    for path in (database, lock_path):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise InstallError('UNSAFE_DATA_PATH', 'A private workspace path is not a regular file.')
    with lock_path.open('a+b') as lock:
        lock_path.chmod(0o600)
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise InstallError('WORKSPACE_BUSY', 'Stop the existing Haven process before initializing its owner.') from None
        connection = sqlite3.connect(database, timeout=10)
        try:
            database.chmod(0o600)
            connection.execute('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
            connection.commit()
            yield connection
        finally:
            connection.close()
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def provision_owner(data_directory, password_reader=None, terminal_check=None):
    """Tests inject inputs; production accepts passwords only through getpass."""
    with owner_database(data_directory) as connection:
        row = connection.execute("SELECT value FROM settings WHERE key='password'").fetchone()
        if row:
            try:
                existing = json.loads(row[0])
                valid = (isinstance(existing, dict)
                         and re.fullmatch('[0-9a-f]{32}', existing.get('salt', ''))
                         and re.fullmatch('[0-9a-f]{64}', existing.get('hash', '')))
            except (ValueError, TypeError):
                valid = False
            if not valid:
                raise InstallError('OWNER_RECORD_INVALID', 'The existing owner record needs private recovery; it was not replaced.')
            return 'preserved'
        terminal_check = terminal_check or sys.stdin.isatty
        if not terminal_check():
            raise InstallError('OWNER_TERMINAL_REQUIRED', 'Open the private hosting console to enter the owner password; never send it in chat.')
        reader = password_reader or getpass.getpass
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            try:
                password = reader('Choose your private Haven password (12–256 characters): ')
                confirmation = reader('Enter it again: ')
            except getpass.GetPassWarning:
                raise InstallError('OWNER_TERMINAL_REQUIRED', 'This console cannot hide password input safely.') from None
        if not isinstance(password, str) or not 12 <= len(password) <= 256:
            raise InstallError('PASSWORD_LENGTH', 'The owner password must contain 12–256 characters; no password was saved.')
        if password != confirmation:
            raise InstallError('PASSWORD_MISMATCH', 'The password entries did not match; no password was saved.')
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), PASSWORD_ITERATIONS).hex()
        encoded = json.dumps({'salt': salt, 'hash': digest})
        password = confirmation = ''
        connection.execute('BEGIN IMMEDIATE')
        if connection.execute("SELECT 1 FROM settings WHERE key='password'").fetchone():
            connection.rollback()
            return 'preserved'
        connection.execute('INSERT INTO settings(key,value) VALUES(?,?)', ('password', encoded))
        connection.commit()
        return 'created'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-sha256')
    parser.add_argument('--internal-smoke', nargs=2, metavar=('SOURCE', 'DATA'), help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    os.umask(0o077)
    if arguments.internal_smoke:
        try:
            smoke_test(*arguments.internal_smoke)
            return 0
        except Exception:
            return 2
    home = Path.home()
    installation = home / 'haven-install'
    source = home / 'haven'
    phase = 'verifying_archive'
    def stage(name, **fields):
        nonlocal phase
        phase = name
        write_status(installation, name, **fields)
        print('Haven installation: ' + name.replace('_', ' '), flush=True)
    try:
        if sys.version_info < (3, 11):
            raise InstallError('PYTHON_VERSION', 'Haven requires Python 3.11 or newer.')
        stage(phase)
        verify_archive(installation / 'haven-source.zip', arguments.archive_sha256)
        used_before = check_capacity(home)
        stage('extracting_source', approximate_home_bytes=used_before)
        extract_source(installation / 'haven-source.zip', source)
        stage('installing_dependencies')
        python, environment = prepare_environment(home, source)
        stage('checking_capacity')
        used_after = check_capacity(home)
        stage('running_smoke_tests', approximate_home_bytes=used_after)
        with tempfile.TemporaryDirectory(prefix='.haven-smoke-', dir=home) as temporary:
            run_quiet([str(python), str(Path(__file__).resolve()), '--internal-smoke', str(source), temporary],
                      environment, 'SMOKE_TEST_FAILED', 'Synthetic hosting checks failed; no public application was enabled.', timeout=120)
        stage('awaiting_owner_password')
        owner = provision_owner(home / 'haven-data')
        used_final = check_capacity(home)
        stage('ready_for_web_configuration', owner=owner, approximate_home_bytes=used_final,
              allocation_is_provider_quota=False, application_payload_quota_mib=64,
              public_webapp_created=False, synthetic_smoke_passed=True)
        print('Owner initialization is complete. No public web application was created.', flush=True)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        code = error.code if isinstance(error, InstallError) else 'PRIVATE_INSTALLATION_STOPPED'
        message = str(error) if isinstance(error, InstallError) else 'Private installation stopped; no public application was enabled. No secret was logged.'
        try:
            write_status(installation, 'failed', failed_stage=phase, error_code=code, message=message,
                         public_webapp_created=False)
        except Exception:
            pass
        print(message, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
