import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import database as db
from auth import validate_init_data
from config import ADMIN_IDS


# ─── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Auth dependency ───────────────────────────────────────────────────────────

def get_current_user(x_init_data: str = Header(...)):
    user = validate_init_data(x_init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid initData")
    return user


def get_admin_user(user: dict = Depends(get_current_user)):
    if user["id"] not in ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Not an admin")
    return user


# ─── Models ────────────────────────────────────────────────────────────────────

class TournamentCreate(BaseModel):
    name: str
    date: Optional[str] = None


class TournamentUpdate(BaseModel):
    status: Optional[str] = None
    registration_open: Optional[bool] = None


class WinnerSet(BaseModel):
    user_id: int
    place: int


# ─── User endpoints ────────────────────────────────────────────────────────────

@app.get("/api/me")
async def get_me(user: dict = Depends(get_current_user)):
    await db.upsert_user(user["id"], user.get("username"), user.get("first_name"))
    return {"ok": True, "user": user, "is_admin": user["id"] in ADMIN_IDS}


@app.get("/api/tournaments/upcoming")
async def list_upcoming(user: dict = Depends(get_current_user)):
    tournaments = await db.get_upcoming_tournaments()
    result = []
    for t in tournaments:
        participants = await db.get_participants(t["id"])
        active_count = sum(1 for p in participants if not p["excluded"])
        is_reg = await db.is_registered(t["id"], user["id"])
        result.append({
            "id": t["id"],
            "name": t["name"],
            "date": t["date"],
            "status": t["status"],
            "registration_open": bool(t["registration_open"]),
            "participants_count": active_count,
            "is_registered": is_reg,
        })
    return result


@app.get("/api/tournaments/completed")
async def list_completed(user: dict = Depends(get_current_user)):
    tournaments = await db.get_completed_tournaments()
    result = []
    for t in tournaments:
        results = await db.get_results(t["id"])
        winners = {}
        for r in results:
            winners[r["place"]] = {
                "user_id": r["tg_id"],
                "name": r["first_name"] or r["username"] or f"id{r['tg_id']}",
                "username": r["username"],
            }
        result.append({
            "id": t["id"],
            "name": t["name"],
            "date": t["date"],
            "winners": winners,
        })
    return result


@app.get("/api/leaderboard")
async def leaderboard(user: dict = Depends(get_current_user)):
    rows = await db.get_leaderboard()
    result = []
    for i, row in enumerate(rows, start=1):
        result.append({
            "rank": i,
            "user_id": row["tg_id"],
            "name": row["first_name"] or row["username"] or f"id{row['tg_id']}",
            "username": row["username"],
            "points": row["points"],
            "wins": row["wins"],
            "seconds": row["seconds"],
            "thirds": row["thirds"],
        })
    return result


@app.get("/api/profile")
async def profile(user: dict = Depends(get_current_user)):
    await db.upsert_user(user["id"], user.get("username"), user.get("first_name"))
    results = await db.get_user_results(user["id"])
    history = []
    for r in results:
        history.append({
            "tournament_id": r["tournament_id"],
            "tournament_name": r["name"],
            "date": r["date"],
            "place": r["place"],
        })
    total_points = sum({1: 3, 2: 2, 3: 1}.get(r["place"], 0) for r in results)
    return {
        "user_id": user["id"],
        "name": user.get("first_name") or user.get("username") or f"id{user['id']}",
        "username": user.get("username"),
        "total_points": total_points,
        "history": history,
    }


@app.post("/api/tournaments/{tid}/register")
async def register(tid: int, user: dict = Depends(get_current_user)):
    await db.upsert_user(user["id"], user.get("username"), user.get("first_name"))
    t = await db.get_tournament(tid)
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if not t["registration_open"]:
        raise HTTPException(status_code=400, detail="Registration is closed")
    ok = await db.register_participant(tid, user["id"])
    return {"ok": ok}


@app.post("/api/tournaments/{tid}/unregister")
async def unregister(tid: int, user: dict = Depends(get_current_user)):
    t = await db.get_tournament(tid)
    if not t or not t["registration_open"]:
        raise HTTPException(status_code=400, detail="Registration is closed")
    await db.unregister_participant(tid, user["id"])
    return {"ok": True}


# ─── Admin endpoints ──────────────────────────────────────────────────────────

@app.get("/api/admin/tournaments")
async def admin_list_tournaments(user: dict = Depends(get_admin_user)):
    tournaments = await db.get_all_tournaments()
    result = []
    for t in tournaments:
        participants = await db.get_participants(t["id"])
        results = await db.get_results(t["id"])
        winners = {}
        for r in results:
            winners[str(r["place"])] = {
                "user_id": r["tg_id"],
                "name": r["first_name"] or r["username"] or f"id{r['tg_id']}",
            }
        result.append({
            "id": t["id"],
            "name": t["name"],
            "date": t["date"],
            "status": t["status"],
            "registration_open": bool(t["registration_open"]),
            "participants_count": sum(1 for p in participants if not p["excluded"]),
            "winners": winners,
        })
    return result


@app.post("/api/admin/tournaments")
async def admin_create_tournament(
    body: TournamentCreate,
    user: dict = Depends(get_admin_user),
):
    tid = await db.create_tournament(body.name, body.date)
    return {"ok": True, "id": tid}


@app.patch("/api/admin/tournaments/{tid}")
async def admin_update_tournament(
    tid: int,
    body: TournamentUpdate,
    user: dict = Depends(get_admin_user),
):
    t = await db.get_tournament(tid)
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    if body.status is not None:
        await db.update_tournament_status(tid, body.status)
    if body.registration_open is not None:
        await db.update_registration(tid, body.registration_open)
    return {"ok": True}


@app.delete("/api/admin/tournaments/{tid}")
async def admin_delete_tournament(tid: int, user: dict = Depends(get_admin_user)):
    await db.delete_tournament(tid)
    return {"ok": True}


@app.post("/api/admin/tournaments/{tid}/winners")
async def admin_set_winner(
    tid: int,
    body: WinnerSet,
    user: dict = Depends(get_admin_user),
):
    await db.set_result(tid, body.user_id, body.place)
    return {"ok": True}


@app.delete("/api/admin/tournaments/{tid}/winners/{place}")
async def admin_remove_winner(
    tid: int, place: int, user: dict = Depends(get_admin_user)
):
    results = await db.get_results(tid)
    for r in results:
        if r["place"] == place:
            await db.remove_result(tid, r["tg_id"])
    return {"ok": True}


@app.get("/api/admin/tournaments/{tid}/participants")
async def admin_get_participants(tid: int, user: dict = Depends(get_admin_user)):
    participants = await db.get_participants(tid)
    return [
        {
            "user_id": p["tg_id"],
            "name": p["first_name"] or p["username"] or f"id{p['tg_id']}",
            "username": p["username"],
            "excluded": bool(p["excluded"]),
        }
        for p in participants
    ]


@app.post("/api/admin/tournaments/{tid}/participants/{uid}/exclude")
async def admin_exclude(tid: int, uid: int, user: dict = Depends(get_admin_user)):
    await db.exclude_participant(tid, uid)
    return {"ok": True}


@app.post("/api/admin/tournaments/{tid}/participants/{uid}/include")
async def admin_include(tid: int, uid: int, user: dict = Depends(get_admin_user)):
    await db.include_participant(tid, uid)
    return {"ok": True}


# ─── Serve frontend ────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    return FileResponse("static/index.html")
