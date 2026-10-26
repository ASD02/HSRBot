import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
    PRIMARY KEY (guild_id, key)
);
CREATE TABLE IF NOT EXISTS links (
    user_id INTEGER PRIMARY KEY, uid TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS codes (
    code TEXT PRIMARY KEY, rewards TEXT NOT NULL DEFAULT '', added_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS code_posts (
    guild_id INTEGER NOT NULL, code TEXT NOT NULL, PRIMARY KEY (guild_id, code)
);
CREATE TABLE IF NOT EXISTS uid_board (
    guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, uid TEXT NOT NULL,
    region TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (guild_id, user_id)
);
CREATE TABLE IF NOT EXISTS sent_markers (
    marker TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS snapshots (
    user_id INTEGER NOT NULL, uid TEXT NOT NULL, taken_at TEXT NOT NULL,
    achievements INTEGER, characters INTEGER, world_level INTEGER, level INTEGER,
    PRIMARY KEY (user_id, taken_at)
);
CREATE TABLE IF NOT EXISTS warp_records (
    user_id INTEGER NOT NULL, record_id TEXT NOT NULL, banner TEXT NOT NULL,
    item TEXT NOT NULL, rarity INTEGER NOT NULL, time TEXT NOT NULL,
    PRIMARY KEY (user_id, record_id)
);
CREATE TABLE IF NOT EXISTS hoyolab (
    user_id INTEGER PRIMARY KEY, ltuid TEXT NOT NULL, ltoken_enc BLOB NOT NULL,
    uid TEXT, checkin INTEGER NOT NULL DEFAULT 0, stamina_alert INTEGER NOT NULL DEFAULT 0,
    last_alert TEXT
);
"""


class Database:
    def __init__(self, path):
        self.path = str(path)
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def execute(self, sql: str, params: tuple = ()) -> int:
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cur.rowcount

    async def fetchone(self, sql: str, params: tuple = ()):
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchone()

    async def fetchall(self, sql: str, params: tuple = ()):
        async with self.conn.execute(sql, params) as cur:
            return await cur.fetchall()

    async def get_conf(self, guild_id: int, key: str) -> str | None:
        row = await self.fetchone(
            "SELECT value FROM guild_config WHERE guild_id=? AND key=?", (guild_id, key))
        return row["value"] if row else None

    async def set_conf(self, guild_id: int, key: str, value: str) -> None:
        await self.execute(
            "INSERT INTO guild_config VALUES (?,?,?) ON CONFLICT(guild_id,key) DO UPDATE SET value=excluded.value",
            (guild_id, key, value))

    async def mark_sent(self, marker: str) -> bool:
        """True if newly marked, False if it was already sent (prevents double-fire)."""
        return await self.execute("INSERT OR IGNORE INTO sent_markers VALUES (?)", (marker,)) == 1
