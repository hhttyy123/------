from urllib.parse import quote


def excel_attachment_headers(filename: str) -> dict[str, str]:
    """Return browser-safe headers for Excel downloads with Chinese filenames."""
    ascii_fallback = "export.xlsx"
    encoded = quote(filename)
    return {
        "Content-Disposition": f"attachment; filename={ascii_fallback}; filename*=UTF-8''{encoded}",
    }
