"""Private, streamed UTF-8 archive with bounded SQLite full-text indexing."""

import codecs
import hashlib
import os
import re
import sqlite3
import stat
import uuid
from contextlib import closing
from pathlib import Path

from .budget import Budget, BudgetError

_BLOCK = 32_768
_OVERLAP = 256
_HEADROOM = 65_536


class Archive:
    def __init__(self, root, budget=None, index_limit_bytes=1_000_000_000):
        self.budget = budget or Budget(root)
        self.root = Path(os.path.abspath(root))
        if self.root != self.budget.root:
            raise ValueError("Archive and budget must share a project root")
        self.index_limit_bytes = int(index_limit_bytes)
        self.data_dir = self.budget.safe_path("data")
        self.db_path = self.budget.safe_path("data/archive.sqlite3")
        with self.budget.writer():
            self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(self.data_dir, 0o700)
            with closing(self._connect()) as db, db:
                db.execute("CREATE TABLE IF NOT EXISTS sources (source_id TEXT PRIMARY KEY, name TEXT, sha256 TEXT, bytes INTEGER, chunk_count INTEGER)")
                db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(source_id UNINDEXED, chunk_index UNINDEXED, text)")
            os.chmod(self.db_path, 0o600)

    def _files(self):
        return [self.budget.safe_path(str(self.db_path.relative_to(self.root)) + suffix)
                for suffix in ("", "-journal", "-wal", "-shm")]

    def _limits(self, db):
        # Reserve three times the database size plus 64 KiB for the rollback
        # journal, page headers and commit overhead. max_page_count also bounds
        # deferred FTS writes at COMMIT, when Python cannot inspect each write.
        self.budget.require_bytes(0)
        own_bytes = sum(path.stat().st_size for path in self._files() if path.exists())
        outside = self.budget.used_bytes() - own_bytes
        capacity = min(self.index_limit_bytes, self.budget.max_bytes - outside)
        page_size = db.execute("PRAGMA page_size").fetchone()[0]
        pages = (capacity - _HEADROOM) // (3 * page_size)
        if pages < max(1, db.execute("PRAGMA page_count").fetchone()[0]):
            raise BudgetError("Insufficient project/index budget including SQLite journal overhead")
        db.execute(f"PRAGMA max_page_count={pages}")

    def _connect(self):
        self._files()  # Reject existing symlink database and journal paths.
        db = sqlite3.connect(self.db_path, timeout=10)
        try:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA temp_store=MEMORY")
            db.execute("PRAGMA synchronous=FULL")
            self._limits(db)
            return db
        except BaseException:
            db.close()
            raise

    @staticmethod
    def _source(source_path):
        path = Path(os.path.abspath(source_path))
        if any(component.is_symlink() for component in (path, *path.parents)):
            raise ValueError("Symlink sources are not allowed")
        handle = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | os.O_NONBLOCK)
        if not stat.S_ISREG(os.fstat(handle).st_mode):
            os.close(handle)
            raise ValueError("Source must be a regular UTF-8 text file")
        return path, os.fdopen(handle, "rb")

    def ingest(self, source_path):
        path, handle = self._source(source_path)
        source_id = uuid.uuid4().hex
        digest, byte_count, count = hashlib.sha256(), 0, 0
        decoder, tail = codecs.getincrementaldecoder("utf-8")("strict"), ""
        try:
            with self.budget.writer(), handle, closing(self._connect()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                while True:
                    raw = handle.read(_BLOCK)
                    digest.update(raw)
                    byte_count += len(raw)
                    text = decoder.decode(raw, final=not raw)
                    if any(ord(char) < 32 and char not in "\t\n\r\f" for char in text):
                        raise ValueError("Source contains binary/control bytes; UTF-8 text required")
                    if text:
                        chunk = tail + text
                        self._limits(db)
                        db.execute("INSERT INTO chunks VALUES (?, ?, ?)", (source_id, count, chunk))
                        count += 1
                        tail = chunk[-_OVERLAP:]
                    if not raw:
                        break
                result = dict(source_id=source_id, sha256=digest.hexdigest(), bytes=byte_count, chunks=count, indexed=True)
                db.execute("INSERT INTO sources VALUES (?, ?, ?, ?, ?)",
                           (source_id, path.name, result["sha256"], byte_count, count))
            return result
        except sqlite3.DatabaseError as error:
            if getattr(error, "sqlite_errorcode", None) == sqlite3.SQLITE_FULL:
                raise BudgetError("SQLite index/project storage budget reached; ingestion rolled back") from error
            raise
        finally:
            handle.close()

    def search(self, question, limit=5):
        # Bound and quote individual Unicode words: user punctuation never
        # becomes SQL or an FTS operator, including quotes, NOT and NEAR().
        tokens = re.findall(r"\w+", str(question)[:8192], flags=re.UNICODE)[:32]
        if not tokens:
            return []
        query = " OR ".join('"' + token.replace('"', '""') + '"' for token in tokens)
        limit = max(0, min(int(limit), 50))
        with closing(self._connect()) as db:
            rows = db.execute("SELECT c.source_id, s.name, c.chunk_index, c.text FROM chunks c JOIN sources s ON s.source_id=c.source_id WHERE chunks MATCH ? ORDER BY bm25(chunks), c.rowid LIMIT ?", (query, limit)).fetchall()
        return [dict(id=f"S{number}", source_id=row[0], name=row[1], chunk_index=row[2], text=row[3])
                for number, row in enumerate(rows, 1)]

    def delete(self, source_id):
        with self.budget.writer(), closing(self._connect()) as db, db:
            db.execute("DELETE FROM chunks WHERE source_id=?", (str(source_id),))
            db.execute("DELETE FROM sources WHERE source_id=?", (str(source_id),))
