# HSRBot

A Honkai: Star Rail Discord bot (Python, discord.py, slash commands, SQLite).

## Setup

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows; use .venv/bin/pip on Linux/macOS
cp .env.example .env                            # then fill in DISCORD_TOKEN
.venv/Scripts/python -m hsrbot
```

Invite the bot with the `bot` and `applications.commands` scopes. Set `DEV_GUILD_ID` while developing so commands appear instantly. Run tests with `.venv/Scripts/python -m pytest`.

## Commands

| Area | Commands |
|---|---|
| Warps | `/pity`, `/pullplan`, `/warpsim` |
| Warp history | `/warp import`, `/warp stats`, `/warp clear` |
| Speed | `/av`, `/breakpoint`, `/turnorder` |
| Lookup | `/character`, `/lightcone`, `/refreshdata` (owner) |
| Calendar | `/banners`, `/resets` (+ reminders to the announce channel) |
| Community | `/setup channel|role|region` (admin), `/codes`, `/addcode` (owner), `/leaks`, `/spoiler`, `/uid post|find|remove` |
| Fun | `/trivia`, `/guess` |
| Players | `/link`, `/profile`, `/build`, `/leaderboard` |
| HoYoLAB | `/hoyolab link|notes|stamina_alert|checkin|redeem|unlink` (needs `FERNET_KEY`) |

## Data sources

- Characters, Light Cones, relic substat tables: [StarRailRes](https://github.com/Mar-7th/StarRailRes), cached in `data/cache` for 7 days (`/refreshdata` forces it).
- Player showcases: [Enka.Network](https://enka.network). The player's in-game showcase must be public.
- Warp history: HoYoverse's warp-history endpoint, using the link the player copies from the in-game history page.
- Patch dates and endgame resets: `data/schedule.json`, **maintained by hand**.

## Things to know

- **Schedule dates are estimates.** 4.7 is expected around Nov 9-11, 2026 (unconfirmed), and which endgame mode resets on which date is unverified. Edit `data/schedule.json` when HoYoverse confirms.
- **Relic scoring is a heuristic.** It reports roll efficiency using rough per-Path substat weights, not a per-character build.
- **Profile output is embeds**, not rendered image cards.
- **Capturing Radiance** (the extra 50/50 safety net) is not modelled in the pity math.
- **Codes and news feeds** are optional: set `CODES_URL` (JSON list) and `NEWS_RSS_URL`, or use `/addcode`.
- **HoYoLAB cookies** are encrypted at rest with `FERNET_KEY`, features are opt-in, and `/hoyolab unlink` deletes them immediately. Automated daily check-in may violate HoYoverse's terms; read them before enabling it.
- Never paste a warp link or cookies anywhere public. The bot only accepts them through ephemeral slash commands.
