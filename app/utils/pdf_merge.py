"""Fusion de PDF (facture + BL)."""

from __future__ import annotations

import io
from typing import BinaryIO


def merge_pdf_bytes(*parts: BinaryIO | bytes | None) -> io.BytesIO:
    """Concatène plusieurs PDF en un seul BytesIO."""
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    for part in parts:
        if part is None:
            continue
        if isinstance(part, (bytes, bytearray)):
            raw = io.BytesIO(part)
        else:
            data = part.getvalue() if hasattr(part, "getvalue") else None
            if data is not None:
                raw = io.BytesIO(data)
            else:
                if hasattr(part, "seek"):
                    part.seek(0)
                raw = part
        reader = PdfReader(raw)
        for page in reader.pages:
            writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out
