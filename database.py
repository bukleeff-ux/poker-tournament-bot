import aiosqlite
from typing import Optional

DB_PATH = "tournament.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT,
                status TEXT NOT NULL DEFAULT 'upcoming',
                registration_open INTEGER NOT NULL DEFAULT 0
            )
        """)
        # status: 'upcoming' | 'active' | 'completed'
        await db.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                excluded INTEGER NOT NULL DEFAULT 0,
                UNIQUE(tournament_id, user_id),
                FOREIGN KEY(tournament_id) REFERENCES tournaments(id),
                FOREIGN KEY(user_id) REFERENCES users(tg_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                place INTEGER NOT NULL,
                UNIQUE(tournament_id, user_id),
                FOREIGN KEY(tournament_id) REFERENCES tournaments(id),
                FOREIGN KEY(user_id) REFERENCES users(tg_id)
            )
        """)
        await db.commit()


# ─── Users ────────────────────────────────────────────────────────────────────

async def upsert_user(tg_id: int, username: Optional[str], first_name: Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (tg_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name
        """, (tg_id, username, first_name))
        await db.commit()


async def get_user(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            return await cursor.fetchone()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY first_name") as cursor:
            return await cursor.fetchall()


# ─── Tournaments ──────────────────────────────────────────────────────────────

async def create_tournament(name: str, date: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tournaments (name, date, status) VALUES (?, ?, 'upcoming')",
            (name, date)
        )
        await db.commit()
        return cursor.lastrowid


async def get_tournament(tournament_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,)) as cursor:
            return await cursor.fetchone()


async def get_all_tournaments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tournaments ORDER BY id DESC") as cursor:
            return await cursor.fetchall()


async def get_completed_tournaments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tournaments WHERE status = 'completed' ORDER BY id DESC"
        ) as cursor:
            return await cursor.fetchall()


async def get_upcoming_tournaments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tournaments WHERE status != 'completed' ORDER BY id DESC"
        ) as cursor:
            return await cursor.fetchall()


async def update_tournament_status(tournament_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tournaments SET status = ? WHERE id = ?",
            (status, tournament_id)
        )
        await db.commit()


async def update_registration(tournament_id: int, open_reg: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tournaments SET registration_open = ? WHERE id = ?",
            (1 if open_reg else 0, tournament_id)
        )
        await db.commit()


async def delete_tournament(tournament_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM results WHERE tournament_id = ?", (tournament_id,))
        await db.execute("DELETE FROM participants WHERE tournament_id = ?", (tournament_id,))
        await db.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
        await db.commit()


# ─── Participants ─────────────────────────────────────────────────────────────

async def register_participant(tournament_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO participants (tournament_id, user_id) VALUES (?, ?)",
                (tournament_id, user_id)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def unregister_participant(tournament_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM participants WHERE tournament_id = ? AND user_id = ?",
            (tournament_id, user_id)
        )
        await db.commit()


async def exclude_participant(tournament_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE participants SET excluded = 1 WHERE tournament_id = ? AND user_id = ?",
            (tournament_id, user_id)
        )
        await db.commit()


async def include_participant(tournament_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE participants SET excluded = 0 WHERE tournament_id = ? AND user_id = ?",
            (tournament_id, user_id)
        )
        await db.commit()


async def get_participants(tournament_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT u.tg_id, u.username, u.first_name, p.excluded
            FROM participants p
            JOIN users u ON u.tg_id = p.user_id
            WHERE p.tournament_id = ?
            ORDER BY u.first_name
        """, (tournament_id,)) as cursor:
            return await cursor.fetchall()


async def is_registered(tournament_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM participants WHERE tournament_id = ? AND user_id = ? AND excluded = 0",
            (tournament_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


# ─── Results ──────────────────────────────────────────────────────────────────

async def set_result(tournament_id: int, user_id: int, place: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO results (tournament_id, user_id, place)
            VALUES (?, ?, ?)
            ON CONFLICT(tournament_id, user_id) DO UPDATE SET place=excluded.place
        """, (tournament_id, user_id, place))
        await db.commit()


async def get_results(tournament_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT r.place, u.tg_id, u.username, u.first_name
            FROM results r
            JOIN users u ON u.tg_id = r.user_id
            WHERE r.tournament_id = ?
            ORDER BY r.place
        """, (tournament_id,)) as cursor:
            return await cursor.fetchall()


async def get_user_results(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT r.place, r.tournament_id, t.name, t.date
            FROM results r
            JOIN tournaments t ON t.id = r.tournament_id
            WHERE r.user_id = ?
            ORDER BY t.id DESC
        """, (user_id,)) as cursor:
            return await cursor.fetchall()


async def remove_result(tournament_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM results WHERE tournament_id = ? AND user_id = ?",
            (tournament_id, user_id)
        )
        await db.commit()


# ─── Leaderboard ──────────────────────────────────────────────────────────────

async def get_leaderboard():
    """Returns users sorted by total points (1st=3, 2nd=2, 3rd=1)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT
                u.tg_id,
                u.username,
                u.first_name,
                SUM(CASE r.place WHEN 1 THEN 3 WHEN 2 THEN 2 WHEN 3 THEN 1 ELSE 0 END) AS points,
                SUM(CASE r.place WHEN 1 THEN 1 ELSE 0 END) AS wins,
                SUM(CASE r.place WHEN 2 THEN 1 ELSE 0 END) AS seconds,
                SUM(CASE r.place WHEN 3 THEN 1 ELSE 0 END) AS thirds
            FROM users u
            LEFT JOIN results r ON r.user_id = u.tg_id
            GROUP BY u.tg_id
            HAVING points > 0
            ORDER BY points DESC, wins DESC, seconds DESC, thirds DESC
        """) as cursor:
            return await cursor.fetchall()
