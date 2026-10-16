from scrap_master.utils.filetypes import category_of, organize, resolve, sources_for, types_from_text


def test_resolve_presets_aliases_and_raw_exts():
    assert resolve(["pdf"]) == (".pdf",)
    assert ".pptx" in resolve(["powerpoint"]) and ".xlsx" in resolve(["office"])
    assert resolve(["pdf,epub", ".DJVU"]) == (".pdf", ".epub", ".mobi", ".azw3", ".djvu", ".fb2")
    assert resolve(["xyz"]) == (".xyz",)
    assert resolve(None) == (".pdf",)


def test_sources_only_for_document_types():
    assert sources_for((".pdf",)) == ("scribd", "gdrive")
    assert sources_for((".jpg", ".mp4")) == ()


def test_types_from_text():
    assert types_from_text("form 2 physics past papers, pdfs only") == (".pdf",)
    assert ".pptx" in types_from_text("only slides and sheets from moe.go.tz")
    assert types_from_text("biology notes for form 4") is None


def test_category_of():
    assert category_of("a/b/Report.PDF") == "pdf"
    assert category_of("x.pptx") == "slides"
    assert category_of(".epub") == "ebooks"
    assert category_of("noext") == "other"


def test_organize_moves_files_and_keeps_manifest(tmp_path):
    for n in ("a.pdf", "b.docx", "c.pdf", "harvest_manifest.json", "d.weird"):
        (tmp_path / n).write_text(n)
    (tmp_path / "pdf").mkdir()
    (tmp_path / "pdf" / "a.pdf").write_text("old")
    counts = organize(tmp_path)
    assert counts == {"pdf": 2, "docs": 1, "other": 1}
    assert (tmp_path / "pdf" / "a_1.pdf").read_text() == "a.pdf"
    assert (tmp_path / "harvest_manifest.json").exists()
