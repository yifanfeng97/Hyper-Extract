"""CLI input suffix checks for `he parse` and `he feed`.

LLM calls are mocked: Template.create, feed_text, and dump are never real.
Document conversion is exercised through the real reader layer (real
fixtures where conversion runs; monkeypatched availability where the
missing-backend path is tested).
"""

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from hyperextract.cli.cli import app
from hyperextract.utils import readers
from hyperextract.utils.readers import markitdown_available

runner = CliRunner()


def _fixtures_dir():
    from pathlib import Path

    return Path(__file__).parent.parent / "fixtures" / "documents"


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


@contextmanager
def _mock_feed(ka=None):
    ka = ka or _mock_ka()
    with (
        patch("hyperextract.cli.cli.validate_config"),
        patch("hyperextract.cli.cli.Template.create", return_value=ka),
    ):
        yield ka


def _invoke_parse(path, output, input_text=None):
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
    ]
    return runner.invoke(app, args, input=input_text)


def _make_ka(tmp_path):
    ka = tmp_path / "ka"
    ka.mkdir()
    (ka / "data.json").write_text("{}", encoding="utf-8")
    (ka / "metadata.json").write_text(
        json.dumps({"template": "general/graph", "lang": "en"}),
        encoding="utf-8",
    )
    return ka


class TestParseInputTypes:
    def test_txt_md_always_accepted(self, tmp_path):
        notes = tmp_path / "NOTES.TXT"
        notes.write_text("upper txt", encoding="utf-8")
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(notes, out)

        assert result.exit_code == 0
        ka.feed_text.assert_called_once_with("upper txt", source_id=None)

    def test_stdin_is_not_suffix_checked(self, tmp_path):
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse("-", out, input_text="hello from stdin")

        assert result.exit_code == 0
        ka.feed_text.assert_called_once_with("hello from stdin", source_id=None)

    def test_document_input_converted_and_fed(self, tmp_path):
        """With markitdown installed, an HTML file flows through end to end."""
        html = tmp_path / "page.html"
        html.write_text("<html><body><p>parsed body text</p></body></html>")
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(html, out)

        assert result.exit_code == 0, result.output
        ka.feed_text.assert_called_once()
        assert "parsed body text" in ka.feed_text.call_args[0][0]

    def test_real_pdf_fixture_converted(self, tmp_path):
        pdf = _fixtures_dir() / "sample.pdf"
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(pdf, out)

        assert result.exit_code == 0, result.output
        assert "Hello Hyper Extract from PDF" in ka.feed_text.call_args[0][0]

    def test_corrupt_document_fails_closed(self, tmp_path):
        pdf = tmp_path / "broken.pdf"
        pdf.write_bytes(b"%PDF-1.4 not a real pdf")
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(pdf, out)

        assert result.exit_code == 1
        ka.feed_text.assert_not_called()
        ka.dump.assert_not_called()

    def test_document_without_backend_rejected_with_hint(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "hyperextract.cli.utils.markitdown_available", lambda: False
        )
        pdf = tmp_path / "notes.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(pdf, out)

        assert result.exit_code == 1
        assert "hyperextract[ingest]" in result.output
        ka.feed_text.assert_not_called()

    def test_unsupported_suffix_lists_formats(self, tmp_path):
        blob = tmp_path / "data.bin"
        blob.write_bytes(b"\x00\x01")
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(blob, out)

        assert result.exit_code == 1
        assert ".txt" in result.output
        ka.feed_text.assert_not_called()

    def test_directory_md_and_pdf_both_read(self, tmp_path):
        folder = tmp_path / "docs"
        folder.mkdir()
        (folder / "a.md").write_text("markdown body", encoding="utf-8")
        (folder / "page.html").write_text("<p>html body</p>")
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(folder, out)

        assert result.exit_code == 0, result.output
        # Per-file provenance: auto-attributed by file stem.
        fed = {call.kwargs.get("source_id") for call in ka.feed_text.call_args_list}
        texts = [call.args[0] for call in ka.feed_text.call_args_list]
        assert fed == {"a", "page"}
        assert any("markdown body" in t for t in texts)
        assert any("html body" in t for t in texts)

    def test_directory_unsupported_only_exits(self, tmp_path):
        folder = tmp_path / "docs"
        folder.mkdir()
        (folder / "data.bin").write_bytes(b"\x00\x01")
        out = tmp_path / "out"
        with _mock_parse() as ka:
            result = _invoke_parse(folder, out)

        assert result.exit_code == 1
        ka.feed_text.assert_not_called()
        ka.dump.assert_not_called()


class TestFeedInputTypes:
    def test_feed_stdin_is_not_suffix_checked(self, tmp_path):
        ka_dir = _make_ka(tmp_path)
        with _mock_feed() as ka:
            result = runner.invoke(
                app,
                ["feed", str(ka_dir), "-"],
                input="feed stdin text",
            )

        assert result.exit_code == 0
        ka.feed_text.assert_called_once_with(
            "feed stdin text", source_id=None, content_hash=None
        )
        ka.dump.assert_called()

    def test_feed_docx_converted(self, tmp_path):
        ka_dir = _make_ka(tmp_path)
        docx = _fixtures_dir() / "sample.docx"
        with _mock_feed() as ka:
            result = runner.invoke(app, ["feed", str(ka_dir), str(docx)])

        assert result.exit_code == 0, result.output
        assert "Hello Hyper Extract from DOCX" in ka.feed_text.call_args[0][0]

    def test_feed_directory_two_txt_sources(self, tmp_path):
        ka_dir = _make_ka(tmp_path)
        folder = tmp_path / "docs"
        folder.mkdir()
        (folder / "alpha.txt").write_text("first document", encoding="utf-8")
        (folder / "beta.txt").write_text("second document", encoding="utf-8")
        with _mock_feed() as ka:
            result = runner.invoke(app, ["feed", str(ka_dir), str(folder)])

        assert result.exit_code == 0, result.output
        ids = [call.kwargs.get("source_id") for call in ka.feed_text.call_args_list]
        texts = [call.args[0] for call in ka.feed_text.call_args_list]
        assert ids == ["alpha", "beta"]
        assert texts == ["first document", "second document"]
        ka.dump.assert_called()

    def test_feed_directory_unsupported_only_exits(self, tmp_path):
        ka_dir = _make_ka(tmp_path)
        folder = tmp_path / "docs"
        folder.mkdir()
        (folder / "data.bin").write_bytes(b"\x00\x01")
        with _mock_feed() as ka:
            result = runner.invoke(app, ["feed", str(ka_dir), str(folder)])

        assert result.exit_code == 1
        ka.feed_text.assert_not_called()
        ka.dump.assert_not_called()

    def test_feed_document_without_backend_rejected_with_hint(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "hyperextract.cli.utils.markitdown_available", lambda: False
        )
        ka_dir = _make_ka(tmp_path)
        docx = tmp_path / "notes.docx"
        docx.write_bytes(b"PK fake docx")
        with _mock_feed() as ka:
            result = runner.invoke(app, ["feed", str(ka_dir), str(docx)])

        assert result.exit_code == 1
        assert "hyperextract[ingest]" in result.output
        ka.feed_text.assert_not_called()
        ka.dump.assert_not_called()


def test_feed_directory_writes_two_sources_to_ledger(tmp_path):
    """Two txt files become two AutoDocument source-ledger entries after feed."""
    from hyperextract.types import AutoDocument
    from tests.mocks import MockChatModel, MockEmbeddings

    ka_dir = tmp_path / "ka"
    seed = AutoDocument(llm_client=MockChatModel(), embedder=MockEmbeddings())
    seed.metadata["template"] = "general/graph"
    seed.metadata["lang"] = "en"
    seed.dump(ka_dir)

    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "alpha.txt").write_text("first document", encoding="utf-8")
    (folder / "beta.txt").write_text("second document", encoding="utf-8")

    live = AutoDocument(llm_client=MockChatModel(), embedder=MockEmbeddings())
    with (
        patch("hyperextract.cli.cli.validate_config"),
        patch("hyperextract.cli.cli.Template.create", return_value=live),
    ):
        result = runner.invoke(app, ["feed", str(ka_dir), str(folder)])

    assert result.exit_code == 0, result.output
    assert set(live.sources()) == {"alpha", "beta"}
    data = json.loads((ka_dir / "data.json").read_text(encoding="utf-8"))
    assert len(data.get("chunks", [])) == 2
    ledger = json.loads((ka_dir / "sources_chunks.json").read_text(encoding="utf-8"))
    assert {entry["source_id"] for entry in ledger} == {"alpha", "beta"}


def test_backend_probe_function_exists():
    # Direct sanity check so the import surface stays stable.
    assert callable(markitdown_available)
    assert callable(readers.read_document)
