from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def build_paginated_urls(
    url: str,
    *,
    max_pages: int = 10,
    page_size: int = 30,
    first_page: int = 1,
) -> list[str]:
    """Expand a public Superbid listing URL using its documented pageNumber/pageSize pattern.

    Existing filters/order/searchType are preserved. We deliberately do not invent
    category slugs or force searchType; the caller supplies a verified listing URL.
    """
    max_pages = max(1, min(int(max_pages), 100))
    page_size = max(1, min(int(page_size), 200))
    first_page = max(1, int(first_page))

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["pageSize"] = str(page_size)

    out = []
    for page in range(first_page, first_page + max_pages):
        q = dict(query)
        q["pageNumber"] = str(page)
        out.append(urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment)))
    return out


def is_paginated_source(source_type: str | None) -> bool:
    return (source_type or "").strip().lower() in {"paginated", "category_paginated", "search_paginated"}
