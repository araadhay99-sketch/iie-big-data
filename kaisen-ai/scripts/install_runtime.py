"""Install a publisher-pinned CPU runtime; never download a model or start a server."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kaisen.budget import Budget
from kaisen.model import HTTPSRedirects


class RuntimeError(ValueError):
    """The pinned runtime could not be safely installed."""


def load_manifest(path):
    return validate_manifest(json.loads(Path(path).read_text()))


def validate_manifest(value):
    tag, name = value.get('tag', ''), value.get('filename', '')
    if (not re.fullmatch(r'b[0-9]+', tag)
            or not re.fullmatch(r'[0-9a-f]{40}', value.get('revision', ''))
            or not re.fullmatch(r'[0-9a-f]{64}', value.get('sha256', ''))
            or name != f'llama-{tag}-bin-ubuntu-x64.tar.gz'
            or type(value.get('size_bytes')) is not int or not 0 < value['size_bytes'] <= 64 * 1024**2
            or value.get('download_url') != f'https://github.com/ggml-org/llama.cpp/releases/download/{tag}/{name}'):
        raise RuntimeError('Invalid pinned official CPU runtime manifest.')
    return value


def archive_members(archive, destination, budget, max_members=512, max_bytes=512 * 1024**2):
    """Validate the full archive before extraction, including contained links."""
    members, names, total = [], set(), 0
    for member in archive:
        path = PurePosixPath(member.name)
        if (len(members) >= max_members or path.is_absolute() or '..' in path.parts
                or '\\' in member.name or path.as_posix() in names
                or not (member.isdir() or member.isfile() or member.issym())):
            raise RuntimeError('Unsafe archive path, duplicate, member type or member count.')
        if member.issym():
            link = PurePosixPath(member.linkname)
            target = destination / path.parent / link
            if (link.is_absolute() or '\\' in member.linkname
                    or not target.resolve().is_relative_to(destination.resolve())):
                raise RuntimeError('Archive link escapes the runtime directory.')
        total += member.size if member.isfile() else 0
        if member.size < 0 or total > max_bytes:
            raise RuntimeError('Archive exceeds its expanded byte bound.')
        tarfile.data_filter(member, str(destination))
        names.add(path.as_posix()); members.append(member)
    budget.require_bytes(total + 1024**2)
    return members


def install_runtime(root, manifest, opener=None, budget=None, runner=None):
    manifest = validate_manifest(manifest)
    budget, runner = budget or Budget(root), runner or subprocess.run
    with budget.writer():
        runtime = budget.safe_path('runtime')
        runtime.mkdir(mode=0o700, exist_ok=True); runtime.chmod(0o700)
        target = budget.safe_path('runtime/' + manifest['tag'])
        record_path = budget.safe_path('runtime/installed.json')
        if target.exists() or record_path.exists():
            raise RuntimeError('Existing runtime or installation record was preserved; inspect it before retrying.')
        budget.require_bytes(manifest['size_bytes'] + 512 * 1024**2 + 1024**2)
        with tempfile.TemporaryDirectory(prefix='.install-', dir=runtime) as temporary:
            stage = Path(temporary); payload = stage / 'runtime'; payload.mkdir(mode=0o700)
            archive_path = stage / 'download.tar.gz'
            count, checksum = 0, hashlib.sha256()
            try:
                request = Request(manifest['download_url'], headers={'Accept': 'application/octet-stream'})
                with (opener or build_opener(HTTPSRedirects())).open(request, timeout=30) as response:
                    declared = response.headers.get('Content-Length')
                    if declared is not None and int(declared) != manifest['size_bytes']:
                        raise RuntimeError('Runtime download differs from the pinned size.')
                    with archive_path.open('xb') as output:
                        archive_path.chmod(0o600)
                        while chunk := response.read(1024**2):
                            count += len(chunk)
                            if count > manifest['size_bytes']:
                                raise RuntimeError('Runtime download exceeded the pinned size.')
                            budget.require_bytes(len(chunk)); checksum.update(chunk); output.write(chunk)
                        output.flush(); os.fsync(output.fileno())
            except (HTTPError, URLError, TimeoutError) as error:
                detail = f'HTTP {error.code}' if isinstance(error, HTTPError) else type(error).__name__
                raise RuntimeError(f'Runtime download unavailable ({detail}); check approved publisher/CDN networking.') from None
            if count != manifest['size_bytes'] or checksum.hexdigest() != manifest['sha256']:
                raise RuntimeError('Runtime checksum or complete-file size did not verify.')
            with tarfile.open(archive_path, 'r:gz') as archive:
                members = archive_members(archive, payload, budget)
                archive.extractall(payload, members=members, filter='data')
            candidates = [p for p in payload.rglob('llama-server') if p.is_file() and not p.is_symlink()]
            if len(candidates) != 1:
                raise RuntimeError('Runtime must contain exactly one regular llama-server executable.')
            server = candidates[0]
            observations = {}
            for flag in ('--version', '--help'):
                try:
                    result = runner([str(server), flag], capture_output=True, text=True, timeout=30, check=True)
                except (subprocess.SubprocessError, OSError) as error:
                    detail = (getattr(error, 'stderr', '') or str(error))[-2048:]
                    raise RuntimeError(f'Runtime {flag} compatibility check failed: {type(error).__name__}: {detail}') from None
                observations[flag] = (result.stdout + result.stderr)[-131072:]
            flags = [flag for flag in ('--jinja', '--parallel', '--ctx-size', '--threads', '--n-predict', '--host')
                     if re.search(r'(?<![\w-])' + re.escape(flag) + r'(?![\w-])', observations['--help'])]
            if not {'--jinja', '--parallel', '--ctx-size'}.issubset(flags):
                raise RuntimeError('Required bounded server flags are unavailable.')
            record = {**manifest, 'checksum_verified': True, 'runtime_smoke_verified': True,
                      'inference_verified': False, 'server_path': str((target / server.relative_to(payload)).relative_to(root)),
                      'version_output': observations['--version'], 'supported_flags': flags}
            record_data = json.dumps(record, indent=2) + '\n'
            budget.require_bytes(len(record_data.encode()))
            staged_record = stage / 'installed.json'; staged_record.write_text(record_data); staged_record.chmod(0o600)
            with staged_record.open('rb') as handle: os.fsync(handle.fileno())
            payload.rename(target)
            staged_record.replace(record_path)
            return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(); root = args.root.resolve()
    record = install_runtime(root, load_manifest(root / 'runtime-manifest.json'))
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
