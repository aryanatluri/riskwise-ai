import io
import zipfile

import pytest

from app.engine.extraction import ExtractionError, extract_text


def make_docx(paragraphs: list[str]) -> bytes:
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{ns}"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


def test_docx_paragraphs():
    text = extract_text("a.docx", make_docx(["14.2 Vendor shall notify within 5 days.", "21.1 Cap."]))
    assert text.splitlines() == ["14.2 Vendor shall notify within 5 days.", "21.1 Cap."]


def test_docx_entity_expansion_is_blocked():
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    evil = (
        f'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaa">]>'
        f'<w:document xmlns:w="{ns}"><w:body><w:p><w:r><w:t>&a;</w:t></w:r></w:p></w:body></w:document>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", evil)
    with pytest.raises(ExtractionError):
        extract_text("evil.docx", buf.getvalue())


def test_unsupported_and_corrupt():
    with pytest.raises(ExtractionError):
        extract_text("x.exe", b"MZ")
    with pytest.raises(ExtractionError):
        extract_text("x.pdf", b"not a pdf")
