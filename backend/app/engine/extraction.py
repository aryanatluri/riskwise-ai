"""Text extraction from uploaded contracts (PDF, DOCX, TXT)."""

import io
import zipfile

from defusedxml import ElementTree as ET
from pypdf import PdfReader


class ExtractionError(ValueError):
    pass


MAX_DOCX_XML_BYTES = 50 * 1024 * 1024
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_text(filename: str, data: bytes, max_pages: int = 300) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(data))
        except Exception as exc:
            raise ExtractionError("Could not read this PDF") from exc
        if len(reader.pages) > max_pages:
            raise ExtractionError(f"PDF has more than {max_pages} pages")
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        if not text.strip():
            raise ExtractionError("This PDF has no text layer (scanned?). OCR is not supported yet.")
        return text
    if name.endswith(".docx"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                info = z.getinfo("word/document.xml")
                if info.file_size > MAX_DOCX_XML_BYTES:  # zip bomb guard
                    raise ExtractionError("DOCX is too large to process")
                root = ET.fromstring(z.read(info))
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError("Could not read this DOCX") from exc
        paras = []
        for p in root.iter(f"{W_NS}p"):
            t = "".join(n.text or "" for n in p.iter(f"{W_NS}t"))
            if t.strip():
                paras.append(t)
        return "\n".join(paras)
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace")
    raise ExtractionError("Unsupported file type. Upload PDF, DOCX or TXT.")
