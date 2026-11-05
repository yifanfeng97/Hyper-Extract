"""Nested (recursive) directory support for he parse / he feed (#205).

Recursive walk is the default; `--flat` restores the legacy top-level-only
scan. Per-file source ids are the path relative to the walked root, so
same-named files in different subdirectories no longer collide in the
source ledger.
"""

import json
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hyperextract.cli.cli import app

runner = CliRunner()


def _mock_ka():
    ka = MagicMock()
    ka.feed_text = MagicMock(return_value=ka)
    ka.dump = MagicMock()
    ka.load = MagicMock()
    ka.build_index = MagicMock()
    return ka


def _mock_template_config():
    cfg = MagicMock()
    cfg.name = "general/graph"
    return cfg


@contextmanager
def _mock_parse(ka=None):
    ka = ka or _mock_ka()
    with (
        patch("hyperextract.cli.cli.validate_config"),
        patch(
            "hyperextract.cli.cli.Template.get",
            return_value=_mock_template_config(),
        ),
        patch("hyperextract.cli.cli.Template.create", return_value=ka),
    ):
        yield ka


def _invoke_parse(path, output, extra=()):
    args = [
        "parse",
        str(path),
        "-o",
        str(output),
        "-t",
        "general/graph",
        "-l",
        "en",
        "--no-index",
        *extra,
    ]
    return runner.invoke(app, args)


def _tree(root: Path) -> None:
    (root / "a").mkdir(parents=True)
    (root / "a" / "b").mkdir(parents=True)
    (root / "a" / "overview.md").write_text("overview A", encoding="utf-8")
    (root / "a" / "b" / "overview.md").write_text("overview B", encoding="utf-8")
    (root / "top.md").write_text("top level", encoding="utf-8")


class TestNestedParse:
    def test_nested_files_ingested_with_relative_sources(self, tmp_path):
        tree = tmp_path / "docs"
        _tree(tree)
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(tree, out)

        assert result.exit_code == 0, result.output
        fed = {
            call.kwargs.get("source_id"): call.args[0]
            for call in ka.feed_text.call_args_list
        }
        assert set(fed) == {"top", "a/overview", "a/b/overview"}
        assert fed["a/overview"] == "overview A"
        assert fed["a/b/overview"] == "overview B"

    def test_same_name_no_collision(self, tmp_path):
        tree = tmp_path / "docs"
        _tree(tree)
        out = tmp_path / "out"
        with _mock_parse() as ka:
            _invoke_parse(tree, out)

        sources = [
            call.kwargs.get("source_id") for call in ka.feed_text.call_args_list
        ]
        assert len(sources) == len(set(sources)) == 3

    def test_hidden_dirs_pruned(self, tmp_path):
        tree = tmp_path / "docs"
        _tree(tree)
        (tree / ".git").mkdir()
        (tree / ".git" / " leaked.md").write_text("secret", encoding="utf-8")
        (tree / ".git" / "leaked.md").write_text("secret", encoding="utf-8")
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(tree, out)

        assert result.exit_code == 0, result.output
        sources = " ".join(
            str(call.kwargs.get("source_id")) for call in ka.feed_text.call_args_list
        )
        assert ".git" not in sources

    def test_flat_mode_top_level_only(self, tmp_path):
        tree = tmp_path / "docs"
        _tree(tree)
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(tree, out, extra=("--flat",))

        assert result.exit_code == 0, result.output
        fed = {
            call.kwargs.get("source_id"): call.args[0]
            for call in ka.feed_text.call_args_list
        }
        assert set(fed) == {"top"}

    def test_explicit_source_still_overrides(self, tmp_path):
        tree = tmp_path / "docs"
        (tree / "a").mkdir(parents=True)
        (tree / "a" / "one.md").write_text("one", encoding="utf-8")
        (tree / "a" / "two.md").write_text("two", encoding="utf-8")
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(tree, out, extra=("--source", "my-corpus"))

        assert result.exit_code == 0, result.output
        assert {
            call.kwargs.get("source_id") for call in ka.feed_text.call_args_list
        } == {"my-corpus"}

    def test_unsupported_files_skipped_with_warning(self, tmp_path):
        tree = tmp_path / "docs"
        (tree / "sub").mkdir(parents=True)
        (tree / "sub" / "keep.md").write_text("keep", encoding="utf-8")
        (tree / "sub" / "drop.bin").write_bytes(b"\x00\x01")
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(tree, out)

        assert result.exit_code == 0, result.output
        assert "drop.bin" in result.output
        assert any(
            call.kwargs.get("source_id") == "sub/keep"
            for call in ka.feed_text.call_args_list
        )


class TestNestedFeed:
    @staticmethod
    def _make_ka(tmp_path):
        ka = MagicMock()
        ka.feed_text = MagicMock(return_value=ka)
        ka.dump = MagicMock()
        ka.load = MagicMock()
        ka_dir = tmp_path / "ka"
        ka_dir.mkdir()
        (ka_dir / "data.json").write_text("{}", encoding="utf-8")
        (ka_dir / "metadata.json").write_text(
            json.dumps({"template": "general/graph", "lang": "en"}),
            encoding="utf-8",
        )
        return ka, ka_dir

    @staticmethod
    def _patches(ka):
        from contextlib import ExitStack

        from hyperextract.utils.template_engine.template import Template as T

        stack = ExitStack()
        stack.enter_context(patch("hyperextract.cli.cli.validate_config"))
        stack.enter_context(patch.object(T, "create", return_value=ka))
        return stack

    def test_feed_directory_recursive(self, tmp_path):
        ka, ka_dir = self._make_ka(tmp_path)
        tree = tmp_path / "docs"
        _tree(tree)

        with self._patches(ka):
            result = runner.invoke(
                app, ["feed", str(ka_dir), str(tree), "--no-store-doc"]
            )

        assert result.exit_code == 0, result.output
        fed = {
            call.kwargs.get("source_id"): call.args[0]
            for call in ka.feed_text.call_args_list
        }
        assert set(fed) == {"top", "a/overview", "a/b/overview"}

    def test_feed_flat_mode_top_level_only(self, tmp_path):
        ka, ka_dir = self._make_ka(tmp_path)
        tree = tmp_path / "docs"
        _tree(tree)

        with self._patches(ka):
            result = runner.invoke(
                app, ["feed", str(ka_dir), str(tree), "--flat", "--no-store-doc"]
            )

        assert result.exit_code == 0, result.output
        fed = {
            call.kwargs.get("source_id"): call.args[0]
            for call in ka.feed_text.call_args_list
        }
        assert set(fed) == {"top"}
