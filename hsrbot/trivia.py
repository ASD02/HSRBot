import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    prompt: str
    answer: str
    options: list


def make_question(characters: dict, rng: random.Random, kind: str | None = None) -> Question | None:
    """kind: 'element' | 'path' | 'guess'. None if there is too little data for 4 options."""
    chars = [c for c in characters.values() if c.get("name") and c.get("element") and c.get("path")]
    if len(chars) < 4:
        return None
    kind = kind or rng.choice(["element", "path", "guess"])
    target = rng.choice(chars)
    if kind == "guess":
        pool = [c["name"] for c in chars if c["name"] != target["name"]]
        prompt = (f"Which character is a {target.get('rarity', '?')}★ {target['element']} "
                  f"unit on the Path of {target['path']}?")
        # other characters sharing every hint would make the question ambiguous
        pool = [n for n in pool if not any(
            c["name"] == n and c["element"] == target["element"] and c["path"] == target["path"]
            and c.get("rarity") == target.get("rarity") for c in chars)]
        answer = target["name"]
    else:
        pool = sorted({c[kind] for c in chars} - {target[kind]})
        answer = target[kind]
        prompt = f"What is {target['name']}'s {'element' if kind == 'element' else 'Path'}?"
    if len(pool) < 3:
        return None
    options = rng.sample(pool, 3) + [answer]
    rng.shuffle(options)
    return Question(prompt, answer, options)
