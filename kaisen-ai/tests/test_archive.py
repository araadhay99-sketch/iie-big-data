import hashlib
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from kaisen.archive import Archive
from kaisen.budget import Budget, BudgetError


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "project"
        self.archive = Archive(self.root, Budget(self.root, 12_000_000), index_limit_bytes=10_000_000)

    def source(self, name, contents):
        path = self.base / name
        path.write_bytes(contents)
        return path

    def test_large_source_late_passage_and_fingerprint(self):
        content = b"Ordinary observations of the sky.\n" * 10000 + b"Late discovery: quasiparticle zephyr."
        result = self.archive.ingest(self.source("observations.txt", content))
        self.assertGreater(result["chunks"], 8)
        self.assertEqual(result["bytes"], len(content))
        self.assertEqual(result["sha256"], hashlib.sha256(content).hexdigest())
        self.assertTrue(result["indexed"])
        hits = self.archive.search("quasiparticle")
        self.assertEqual(hits[0]["id"], "S1")
        self.assertEqual(hits[0]["source_id"], result["source_id"])
        self.assertGreater(hits[0]["chunk_index"], 8)
        self.assertIn("quasiparticle zephyr", hits[0]["text"])

    def test_incremental_unicode_boundary(self):
        content = ("x" * 32767 + "界 café telescope " + "🪐" * 18000).encode("utf-8")
        self.archive.ingest(self.source("unicode.txt", content))
        self.assertIn("界 café telescope", self.archive.search("telescope")[0]["text"])
        self.assertTrue(all("�" not in hit["text"] for hit in self.archive.search("café")))

    def test_budget_rollback_preserves_previous_source(self):
        first = self.archive.ingest(self.source("first.txt", b"previous nebula record"))
        self.archive.index_limit_bytes = 350_000
        huge = self.source("large.txt", b"newconstellation " * 100000)
        with self.assertRaises(BudgetError):
            self.archive.ingest(huge)
        hits = self.archive.search("nebula")
        self.assertEqual(hits[0]["source_id"], first["source_id"])
        self.assertEqual(self.archive.search("newconstellation"), [])
        self.assertFalse(Path(str(self.archive.db_path) + "-journal").exists())
        self.assertLessEqual(sum(p.stat().st_size for p in self.archive.data_dir.iterdir()), 350_000)

    def test_invalid_utf8_and_null_reject_entire_ingestion(self):
        self.archive.ingest(self.source("good.txt", b"surviving comet"))
        for number, suffix in enumerate((b"\xff", b"\x00")):
            with self.subTest(suffix=suffix), self.assertRaises((ValueError, UnicodeDecodeError)):
                self.archive.ingest(self.source(f"bad{number}.txt", b"rollbackword " * 4000 + suffix))
        self.assertEqual(self.archive.search("rollbackword"), [])
        self.assertTrue(self.archive.search("comet"))

    def test_query_punctuation_is_data(self):
        self.archive.ingest(self.source("safe.txt", b"nebula and gravity"))
        self.assertTrue(self.archive.search('nebula" OR 1=1; DROP TABLE sources; --'))
        self.assertEqual(self.archive.search('" () + - * : ;'), [])
        self.assertTrue(self.archive.search("gravity"))

    def test_delete_only_selected_source(self):
        first = self.archive.ingest(self.source("first.txt", b"mercury sharedword"))
        self.archive.ingest(self.source("second.txt", b"venus sharedword"))
        self.archive.delete(first["source_id"])
        self.assertEqual(self.archive.search("mercury"), [])
        self.assertEqual(len(self.archive.search("sharedword")), 1)

    def test_budget_counts_regular_files_and_denies_unsafe_paths(self):
        outside = self.source("outside", b"z" * 10000)
        (self.root / "shortcut").symlink_to(outside)
        (self.root / "linked-dir").symlink_to(self.base, target_is_directory=True)
        expected = sum(p.stat().st_size for p in self.archive.data_dir.iterdir())
        self.assertEqual(self.archive.budget.used_bytes(), expected)
        for path in ("../escape", "shortcut", "linked-dir/new"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.archive.budget.safe_path(path)
        with self.assertRaises(ValueError):
            self.archive.ingest(self.root / "shortcut")
        with self.assertRaises(BudgetError):
            self.archive.budget.require_bytes(12_000_000)

    def test_index_symlink_is_rejected_without_touching_target(self):
        self.archive.db_path.unlink()
        target = self.source("untouched", b"private target")
        self.archive.db_path.symlink_to(target)
        with self.assertRaises(ValueError):
            Archive(self.root)
        self.assertEqual(target.read_bytes(), b"private target")

    def test_managed_writer_contention_and_exception_release(self):
        first = self.archive.ingest(self.source("original.txt", b"original nebula"))
        incoming = self.source("incoming.txt", b"later pulsar")
        def competing_writer():
            with Budget(self.root).writer():
                self.fail("Concurrent managed writer acquired an already held lock")
        with self.archive.budget.writer():
            with self.assertRaises(BudgetError):
                with self.archive.budget.writer():
                    self.fail("Nested writer acquired an already held lock")
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaises(BudgetError):
                    pool.submit(competing_writer).result(timeout=2)
            for action in (lambda: Archive(self.root),
                           lambda: self.archive.ingest(incoming),
                           lambda: self.archive.delete(first["source_id"])):
                with self.assertRaises(BudgetError):
                    action()
            self.assertEqual(self.archive.search("nebula")[0]["source_id"], first["source_id"])
        with self.assertRaises(RuntimeError):
            with self.archive.budget.writer():
                raise RuntimeError("Aborted managed write")
        self.archive.ingest(incoming)
        self.archive.delete(first["source_id"])
        self.assertTrue(self.archive.search("pulsar"))
        self.assertEqual(self.archive.search("nebula"), [])


if __name__ == "__main__":
    unittest.main()
