#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
#
# The same floor as the script under test, for a different reason.  This file
# loads the script with SourceFileLoader.exec_module(), so `import tomllib` runs
# in *this* interpreter and the script's own shebang is never consulted — the
# floor has to be restated here or the tests can be run under a Python the script
# could not survive.
#
# That only holds if this file is executed directly:
#
#     ./runbooks/tests/test_brew_bundle_audit.py
#
# `python3 -m unittest discover -s runbooks/tests` still works, but it chooses the
# interpreter on the command line and never reads the block above, so it bypasses
# the floor.  Prefer the direct form.
"""Focused unit tests for the receipt-independent Homebrew audit graph."""

from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "dot_local" / "bin" / "executable_brew_bundle_audit"

# exec_module() below writes a bytecode cache next to SCRIPT, i.e. into
# dot_local/bin/__pycache__/ in the source tree.  That directory has no chezmoi
# prefix, so chezmoi treats it as a source entry and materialises it as
# ~/.local/bin/__pycache__/ on the next apply.  A .gitignore rule would not help:
# chezmoi builds source state from the working tree, not from git's index.  And
# because dot_local/bin is deliberately not exact_ (R1), the junk would never be
# cleaned up again.  Suppress the write instead of ignoring the artefact.
sys.dont_write_bytecode = True

LOADER = importlib.machinery.SourceFileLoader("brew_bundle_audit", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC is not None
audit = importlib.util.module_from_spec(SPEC)
sys.modules[LOADER.name] = audit
LOADER.exec_module(audit)


def formula(
    name: str,
    *,
    dependencies: list[str] | None = None,
    recommended: list[str] | None = None,
    full_name: str | None = None,
    aliases: list[str] | None = None,
    oldnames: list[str] | None = None,
    tap: str = "homebrew/core",
) -> dict[str, object]:
    return {
        "name": name,
        "full_name": full_name or name,
        "tap": tap,
        "aliases": aliases or [],
        "oldnames": oldnames or [],
        "desc": f"Description of {name}",
        "homepage": f"https://example.test/{name}",
        "urls": {"stable": {"url": f"https://source.test/{name}.tar.gz"}},
        "dependencies": dependencies or [],
        "recommended_dependencies": recommended or [],
    }


def cask(
    token: str,
    *,
    formula_dependencies: list[str] | None = None,
    cask_dependencies: list[str] | None = None,
    full_token: str | None = None,
    old_tokens: list[str] | None = None,
    tap: str = "homebrew/cask",
) -> dict[str, object]:
    return {
        "token": token,
        "full_token": full_token or token,
        "tap": tap,
        "old_tokens": old_tokens or [],
        "desc": f"Description of {token}",
        "homepage": f"https://example.test/{token}",
        "url": f"https://download.test/{token}.dmg",
        "depends_on": {
            "formula": formula_dependencies or [],
            "cask": cask_dependencies or [],
        },
    }


class GraphTests(unittest.TestCase):
    def inventory(self, formulae=(), casks=()):
        return audit.build_inventory(
            {"formulae": list(formulae), "casks": list(casks)},
            Path("/nonexistent/cellar"),
            Path("/nonexistent/caskroom"),
        )

    def test_direct_package_and_dependency_are_managed(self):
        inventory = self.inventory([formula("app", dependencies=["library"]), formula("library")])
        result = audit.classify(inventory, {audit.FORMULA: {"app"}, audit.CASK: set()})
        self.assertEqual(result.direct, {audit.PackageID(audit.FORMULA, "app")})
        self.assertEqual(result.managed, set(inventory.packages))
        self.assertFalse(result.roots)

    def test_outside_root_and_dependency(self):
        inventory = self.inventory([formula("tool", dependencies=["library"]), formula("library")])
        result = audit.classify(inventory, {audit.FORMULA: set(), audit.CASK: set()})
        self.assertEqual(result.roots, [audit.PackageID(audit.FORMULA, "tool")])
        self.assertEqual(
            result.outside_dependencies, {audit.PackageID(audit.FORMULA, "library")}
        )

    def test_dependency_shared_with_brewfile_package(self):
        inventory = self.inventory(
            [
                formula("managed", dependencies=["shared"]),
                formula("outside", dependencies=["shared"]),
                formula("shared"),
            ]
        )
        result = audit.classify(inventory, {audit.FORMULA: {"managed"}, audit.CASK: set()})
        self.assertEqual(result.roots, [audit.PackageID(audit.FORMULA, "outside")])
        self.assertEqual(result.shared, {audit.PackageID(audit.FORMULA, "shared")})

    def test_cask_to_cask_dependency(self):
        inventory = self.inventory(casks=[cask("parent", cask_dependencies=["child"]), cask("child")])
        result = audit.classify(inventory, {audit.FORMULA: set(), audit.CASK: set()})
        self.assertEqual(result.roots, [audit.PackageID(audit.CASK, "parent")])
        self.assertIn(audit.PackageID(audit.CASK, "child"), result.outside_dependencies)

    def test_alias_fully_qualified_and_old_cask_token_normalization(self):
        inventory = self.inventory(
            [
                formula(
                    "new-formula",
                    full_name="owner/tap/new-formula",
                    aliases=["old-alias"],
                    oldnames=["older-formula"],
                    tap="owner/tap",
                )
            ],
            [cask("new-cask", old_tokens=["old-cask"])],
        )
        result = audit.classify(
            inventory,
            {audit.FORMULA: {"owner/tap/new-formula"}, audit.CASK: {"old-cask"}},
        )
        self.assertEqual(len(result.direct), 2)
        self.assertFalse(result.unresolved_direct)

    def test_uninstalled_current_dependency_is_filtered(self):
        inventory = self.inventory([formula("tool", dependencies=["not-installed"])])
        node = audit.PackageID(audit.FORMULA, "tool")
        self.assertFalse(inventory.graph[node])

    def test_missing_description_is_marked_incomplete(self):
        item = formula("tool")
        item["desc"] = None
        inventory = self.inventory([item])
        self.assertEqual(
            inventory.incomplete_metadata, {audit.PackageID(audit.FORMULA, "tool")}
        )

    def test_cycle_gets_deterministic_representative(self):
        inventory = self.inventory(
            [formula("a", dependencies=["b"]), formula("b", dependencies=["a"])]
        )
        result = audit.classify(inventory, {audit.FORMULA: set(), audit.CASK: set()})
        expected = audit.PackageID(audit.FORMULA, "a")
        self.assertEqual(result.roots, [expected])
        self.assertEqual(result.cycle_roots, {expected})
        rendered = "\n".join(
            audit.render_tree(
                expected, inventory, result, verbose=False, receipt_hints=False
            )
        )
        self.assertIn("cycle: already visited", rendered)

    def test_repeated_dependency_is_pruned(self):
        inventory = self.inventory(
            [
                formula("root", dependencies=["left", "right"]),
                formula("left", dependencies=["common"]),
                formula("right", dependencies=["common"]),
                formula("common"),
            ]
        )
        result = audit.classify(inventory, {audit.FORMULA: set(), audit.CASK: set()})
        rendered = "\n".join(
            audit.render_tree(
                result.roots[0], inventory, result, verbose=False, receipt_hints=False
            )
        )
        self.assertIn("already shown", rendered)

    def test_tree_labels_types_and_shows_copyable_brewfile_syntax(self):
        inventory = self.inventory(
            [
                formula(
                    "tool",
                    dependencies=["library"],
                    full_name="owner/tap/tool",
                    tap="owner/tap",
                ),
                formula("library"),
            ]
        )
        result = audit.classify(inventory, {audit.FORMULA: set(), audit.CASK: set()})
        rendered = "\n".join(
            audit.render_tree(
                result.roots[0], inventory, result, verbose=False, receipt_hints=False
            )
        )
        self.assertIn("owner/tap/tool [formula] [top-level candidate]", rendered)
        self.assertIn('Add to a Brewfile: brew "owner/tap/tool"', rendered)
        self.assertIn("library [formula] [dependency]", rendered)

    def test_cask_brewfile_syntax_uses_cask_directive(self):
        inventory = self.inventory(
            casks=[cask("app", full_token="owner/tap/app", tap="owner/tap")]
        )
        package = next(iter(inventory.packages.values()))
        self.assertEqual(audit.brewfile_declaration(package), 'cask "owner/tap/app"')


class ReceiptTests(unittest.TestCase):
    def package(self, paths):
        return audit.Package(
            audit.PackageID(audit.FORMULA, "test"),
            "test",
            "test",
            "",
            "",
            "",
            "",
            receipt_paths=list(paths),
        )

    def write_receipt(self, directory: Path, name: str, value=...):
        path = directory / name
        data = {} if value is ... else {"installed_on_request": value}
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_receipt_states(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            true_path = self.write_receipt(directory, "true.json", True)
            false_path = self.write_receipt(directory, "false.json", False)
            no_field = self.write_receipt(directory, "no-field.json")
            invalid = directory / "invalid.json"
            invalid.write_text("{", encoding="utf-8")
            self.assertEqual(audit.receipt_hint(self.package([true_path])), "on request")
            self.assertEqual(
                audit.receipt_hint(self.package([false_path])), "installed as dependency"
            )
            self.assertEqual(
                audit.receipt_hint(self.package([directory / "missing.json"])), "missing"
            )
            self.assertEqual(
                audit.receipt_hint(self.package([no_field])), "missing installed_on_request"
            )
            self.assertEqual(audit.receipt_hint(self.package([invalid])), "invalid")
            self.assertEqual(
                audit.receipt_hint(self.package([true_path, false_path])),
                "conflicting versions",
            )

    def test_receipts_are_not_read_when_flag_is_disabled(self):
        inventory = GraphTests().inventory([formula("tool")])
        result = audit.classify(inventory, {audit.FORMULA: set(), audit.CASK: set()})
        with mock.patch.object(audit, "receipt_hint", side_effect=AssertionError("receipt read")):
            audit.render_tree(
                result.roots[0], inventory, result, verbose=True, receipt_hints=False
            )

    def test_receipt_hint_never_changes_classification(self):
        inventory = GraphTests().inventory([formula("former-brewfile-entry")])
        before = audit.classify(inventory, {audit.FORMULA: set(), audit.CASK: set()})
        package = inventory.packages[before.roots[0]]
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "receipt.json"
            receipt.write_text('{"installed_on_request": true}', encoding="utf-8")
            package.receipt_paths = [receipt]
            self.assertEqual(audit.receipt_hint(package), "on request")
            after = audit.classify(inventory, {audit.FORMULA: set(), audit.CASK: set()})
        self.assertEqual(before.roots, after.roots)


class ConfigurationAndTapTests(unittest.TestCase):
    def test_effective_layers_are_exact_and_optional(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            directory = home / ".config" / "homebrew"
            directory.mkdir(parents=True)
            (directory / "Brewfile").write_text("", encoding="utf-8")
            (directory / "Brewfile.role-personal").write_text("", encoding="utf-8")
            (directory / "Brewfile.role-work").write_text("", encoding="utf-8")
            layers = audit.effective_layers(home, "personal", "iris")
            self.assertEqual([label for label, _ in layers], ["base", "role-personal"])

    def test_tap_supporting_outside_package_is_not_unused(self):
        inventory = GraphTests().inventory(
            [formula("tool", full_name="owner/tap/tool", tap="owner/tap")]
        )
        result = audit.classify(inventory, {audit.FORMULA: set(), audit.CASK: set()})
        lines, unused = audit.tap_report(
            [audit.TapInfo("owner/tap", "https://example.test", {"owner/tap/tool"}, set(), [])],
            set(),
            inventory,
            result,
        )
        self.assertEqual(unused, 0)
        self.assertIn("  Supports outside owner/tap/tool", lines)

    def test_unused_tap(self):
        inventory = GraphTests().inventory()
        result = audit.classify(inventory, {audit.FORMULA: set(), audit.CASK: set()})
        lines, unused = audit.tap_report(
            [audit.TapInfo("owner/tap", "", set(), set(), [])],
            set(),
            inventory,
            result,
        )
        self.assertEqual(unused, 1)
        self.assertIn("  Assessment: apparently unused", lines)


class CliTests(unittest.TestCase):
    def test_closed_stdout_is_handled_quietly(self):
        broken_stdout = mock.Mock()
        broken_stdout.write.side_effect = BrokenPipeError
        broken_stdout.fileno.side_effect = OSError
        with mock.patch.object(audit.sys, "stdout", broken_stdout):
            self.assertFalse(audit.write_stdout("report\n"))

    def test_verbose_help_qualifies_receipt_hints(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
            audit.parse_args(["--help"])
        self.assertIn("combined with --receipt-hints", " ".join(output.getvalue().split()))


if __name__ == "__main__":
    unittest.main()
