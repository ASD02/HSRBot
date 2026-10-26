"""Parsers for the optional redemption-code and news feeds."""
import re
import xml.etree.ElementTree as ET

CODE_RE = re.compile(r"[A-Z0-9]{8,16}")


def parse_codes(payload) -> list[tuple[str, str]]:
    """Accepts ['CODE', ...] or [{'code': 'CODE', 'rewards': '...'}, ...]; drops anything malformed."""
    out = []
    if not isinstance(payload, list):
        return out
    for item in payload:
        code, rewards = (item, "") if isinstance(item, str) else (
            (item.get("code"), str(item.get("rewards", ""))) if isinstance(item, dict) else (None, ""))
        if isinstance(code, str) and CODE_RE.fullmatch(code.strip().upper()):
            out.append((code.strip().upper(), rewards[:200]))
    return out


def parse_rss(text: str, limit: int = 3) -> list[dict]:
    """Newest-first list of {id, title, link} from an RSS 2.0 or Atom feed. [] if unparseable."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    items = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ("item", "entry"):
            continue
        get = lambda n: next((c for c in el if c.tag.rsplit("}", 1)[-1] == n), None)
        title, link = get("title"), get("link")
        gid = get("guid") if get("guid") is not None else get("id")  # Element truthiness = has children
        href = (link.get("href") or link.text) if link is not None else None
        if title is not None and title.text and href and href.startswith(("http://", "https://")):
            items.append({"id": (gid.text if gid is not None and gid.text else href),
                          "title": title.text.strip()[:200], "link": href.strip()})
    return items[:limit]
