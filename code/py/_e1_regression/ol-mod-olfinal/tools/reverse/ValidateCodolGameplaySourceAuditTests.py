#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("ValidateCodolGameplaySourceAudit.py")
SPEC = importlib.util.spec_from_file_location("source_audit", MODULE_PATH)
assert SPEC and SPEC.loader
SOURCE_AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE_AUDIT)


class SourceAuditTests(unittest.TestCase):
    def test_valid_review_and_unreviewed_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/game_server/server_mp/example.cpp"
            source.parent.mkdir(parents=True)
            source.write_text(
                "// CODREF(example): evidence\nvoid Example() {}\n",
                encoding="utf-8",
            )
            other = source.with_name("other.cpp")
            other.write_text("void Other() {}\n", encoding="utf-8")
            catalog = {
                "schema_version": 1,
                "catalog_id": "codol_gameplay_source_audit",
                "scope": {
                    "include": ["src/game_server/server_mp/*.cpp"],
                    "exclude": [],
                },
                "reviews": [
                    {
                        "path": "src/game_server/server_mp/example.cpp",
                        "symbol": "Example",
                        "status": "reviewed_partial",
                        "matrix_ids": ["example"],
                        "marker": "CODREF(example)",
                        "evidence": "reference",
                        "remaining": "missing edge",
                    }
                ],
            }
            matrix = {"entries": [{"id": "example"}]}
            errors, incomplete, partial, statuses, function_audits, audited_blocks = SOURCE_AUDIT.validate(
                root, catalog, matrix
            )
            self.assertEqual(errors, [])
            self.assertEqual(
                incomplete,
                {
                    "src/game_server/server_mp/example.cpp",
                    "src/game_server/server_mp/other.cpp",
                },
            )
            self.assertEqual(partial, {"src/game_server/server_mp/example.cpp"})
            self.assertEqual(statuses["reviewed_partial"], 1)
            self.assertEqual(function_audits, 0)
            self.assertEqual(audited_blocks, 0)

    def test_full_file_coverage_closes_only_that_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/game_server/server_mp/example.cpp"
            source.parent.mkdir(parents=True)
            source.write_text(
                "// OLMOD(example): boundary\nvoid Example() {}\n",
                encoding="utf-8",
            )
            catalog = {
                "schema_version": 1,
                "catalog_id": "codol_gameplay_source_audit",
                "scope": {
                    "include": ["src/game_server/server_mp/*.cpp"],
                    "exclude": [],
                },
                "reviews": [
                    {
                        "path": "src/game_server/server_mp/example.cpp",
                        "symbol": "Example",
                        "coverage": "full_file",
                        "status": "reviewed_project_boundary",
                        "matrix_ids": ["example"],
                        "marker": "OLMOD(example)",
                        "evidence": "complete block classification",
                        "remaining": "native replacement remains",
                    }
                ],
            }
            errors, incomplete, partial, _, _, _ = SOURCE_AUDIT.validate(
                root, catalog, {"entries": [{"id": "example"}]}
            )
            self.assertEqual(errors, [])
            self.assertEqual(incomplete, set())
            self.assertEqual(partial, set())

    def test_rejects_missing_marker_and_unknown_matrix_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/game_server/server_mp/example.cpp"
            source.parent.mkdir(parents=True)
            source.write_text("void Example() {}\n", encoding="utf-8")
            catalog = {
                "schema_version": 1,
                "catalog_id": "codol_gameplay_source_audit",
                "scope": {
                    "include": ["src/game_server/server_mp/*.cpp"],
                    "exclude": [],
                },
                "reviews": [
                    {
                        "path": "src/game_server/server_mp/example.cpp",
                        "symbol": "Example",
                        "status": "reviewed_partial",
                        "matrix_ids": ["unknown"],
                        "marker": "CODREF(unknown)",
                        "evidence": "reference",
                        "remaining": "missing edge",
                    }
                ],
            }
            errors, _, _, _, _, _ = SOURCE_AUDIT.validate(
                root, catalog, {"entries": []}
            )
            self.assertTrue(any("matrix_ids" in error for error in errors))
            self.assertTrue(any("marker is not present" in error for error in errors))

    def test_function_coverage_requires_anchored_classified_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src/game_server/server_mp/example.cpp"
            source.parent.mkdir(parents=True)
            source.write_text(
                "void Example() {\n"
                "  // CODREF(example): native branch\n"
                "}\n"
                "void Next() {}\n",
                encoding="utf-8",
            )
            review = {
                "path": "src/game_server/server_mp/example.cpp",
                "symbol": "Example",
                "coverage": "function",
                "status": "reviewed_partial",
                "matrix_ids": ["example"],
                "marker": "CODREF(example)",
                "range": {"start": "void Example()", "end": "void Next()"},
                "blocks": [
                    {
                        "id": "native_branch",
                        "classification": "native_reference",
                        "marker": "CODREF(example)",
                        "evidence": "reference control flow",
                        "remaining": "CODOL field offset",
                    }
                ],
                "evidence": "function reviewed from entry to exit",
                "remaining": "one field remains",
            }
            catalog = {
                "schema_version": 1,
                "catalog_id": "codol_gameplay_source_audit",
                "scope": {
                    "include": ["src/game_server/server_mp/*.cpp"],
                    "exclude": [],
                },
                "reviews": [review],
            }
            result = SOURCE_AUDIT.validate(
                root, catalog, {"entries": [{"id": "example"}]}
            )
            errors, _, partial, _, function_audits, audited_blocks = result
            self.assertEqual(errors, [])
            self.assertEqual(partial, {"src/game_server/server_mp/example.cpp"})
            self.assertEqual(function_audits, 1)
            self.assertEqual(audited_blocks, 1)

            del review["blocks"]
            errors, *_ = SOURCE_AUDIT.validate(
                root, catalog, {"entries": [{"id": "example"}]}
            )
            self.assertTrue(any("blocks is required" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
