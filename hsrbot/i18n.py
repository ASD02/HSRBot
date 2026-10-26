"""Tiny locale lookup. Add a language by adding a dict; missing keys fall back to English."""
STRINGS = {
    "en": {
        "uid_posted": "Posted your UID to the board.",
        "uid_removed": "Removed your UID from the board.",
        "no_results": "Nothing found.",
        "linked": "Linked UID {uid}.",
        "not_linked": "You haven't linked a UID. Use /link first.",
    },
    "ja": {
        "uid_posted": "UIDを掲示板に投稿しました。",
        "uid_removed": "UIDを掲示板から削除しました。",
        "no_results": "見つかりませんでした。",
        "linked": "UID {uid} を連携しました。",
        "not_linked": "UIDが未連携です。先に /link を使ってください。",
    },
    "zh-CN": {
        "uid_posted": "已将你的UID发布到公告板。",
        "uid_removed": "已从公告板移除你的UID。",
        "no_results": "未找到结果。",
        "linked": "已绑定UID {uid}。",
        "not_linked": "你还没有绑定UID，请先使用 /link。",
    },
    "es-ES": {
        "uid_posted": "Tu UID se ha publicado en el tablón.",
        "uid_removed": "Tu UID se ha quitado del tablón.",
        "no_results": "No se encontró nada.",
        "linked": "UID {uid} vinculado.",
        "not_linked": "No has vinculado un UID. Usa /link primero.",
    },
}


def tr(locale, key: str, **kw) -> str:
    loc = str(locale) if locale else "en"
    table = STRINGS.get(loc) or STRINGS.get(loc.split("-")[0]) or STRINGS["en"]
    return (table.get(key) or STRINGS["en"][key]).format(**kw)
