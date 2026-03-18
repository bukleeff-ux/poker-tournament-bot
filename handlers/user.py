from telegram import Update
from telegram.ext import ContextTypes

import database as db
import keyboards as kb
from config import MEDAL_EMOJI, POINTS


def user_display(row) -> str:
    return row["first_name"] or row["username"] or f"id{row['tg_id']}"


# ─── /start ───────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        f"👋 Привет, <b>{user.first_name}</b>!\n\nДобро пожаловать в покерный клуб.",
        parse_mode="HTML",
        reply_markup=kb.main_menu_kb(),
    )


# ─── Main menu callback ────────────────────────────────────────────────────────

async def cb_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🃏 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=kb.main_menu_kb(),
    )


# ─── Tournaments ──────────────────────────────────────────────────────────────

async def cb_tournaments_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏆 <b>Турниры</b>\n\nВыберите раздел:",
        parse_mode="HTML",
        reply_markup=kb.tournaments_menu_kb(),
    )


async def cb_tournaments_completed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tournaments = await db.get_completed_tournaments()
    if not tournaments:
        text = "✅ <b>Завершённые турниры</b>\n\nПока нет завершённых турниров."
    else:
        lines = ["✅ <b>Завершённые турниры</b>\n"]
        for t in tournaments:
            results = await db.get_results(t["id"])
            winner_row = next((r for r in results if r["place"] == 1), None)
            winner = user_display(winner_row) if winner_row else "—"
            date_str = f" <i>({t['date']})</i>" if t["date"] else ""
            lines.append(f"🏆 <b>{t['name']}</b>{date_str}\n   🥇 Победитель: {winner}")
        text = "\n\n".join(lines)

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.back_to_tournaments_kb(),
    )


async def cb_tournaments_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tournaments = await db.get_upcoming_tournaments()
    if not tournaments:
        text = "📅 <b>Предстоящие турниры</b>\n\nПока нет запланированных турниров."
        await query.edit_message_text(
            text, parse_mode="HTML", reply_markup=kb.back_to_tournaments_kb()
        )
        return

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = []
    for t in tournaments:
        status_icon = "⚡" if t["status"] == "active" else "📅"
        reg_str = " 🔓" if t["registration_open"] else ""
        buttons.append([InlineKeyboardButton(
            f"{status_icon} {t['name']}{reg_str}",
            callback_data=f"tournament:view:{t['id']}"
        )])
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="menu:tournaments")])

    await query.edit_message_text(
        "📅 <b>Предстоящие турниры</b>\n\nВыберите турнир для просмотра:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cb_tournament_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, _, tid = query.data.split(":")
    tournament_id = int(tid)
    user = update.effective_user
    await db.upsert_user(user.id, user.username, user.first_name)

    t = await db.get_tournament(tournament_id)
    if not t:
        await query.edit_message_text("Турнир не найден.", reply_markup=kb.back_to_tournaments_kb())
        return

    participants = await db.get_participants(tournament_id)
    active_count = sum(1 for p in participants if not p["excluded"])
    is_reg = await db.is_registered(tournament_id, user.id)

    status_map = {"upcoming": "Ожидание", "active": "⚡ Идёт", "completed": "✅ Завершён"}
    date_str = f"\n📅 Дата: <i>{t['date']}</i>" if t["date"] else ""
    reg_str = "\n🔓 Регистрация открыта" if t["registration_open"] else "\n🔒 Регистрация закрыта"

    text = (
        f"🏆 <b>{t['name']}</b>\n"
        f"Статус: {status_map.get(t['status'], t['status'])}"
        f"{date_str}"
        f"{reg_str}\n"
        f"👥 Участников: {active_count}\n\n"
        f"🥇 Победитель: <b>Неизвестно</b>"
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.tournament_user_kb(tournament_id, is_reg, bool(t["registration_open"])),
    )


# ─── Registration ─────────────────────────────────────────────────────────────

async def cb_reg_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, _, tid = query.data.split(":")
    tournament_id = int(tid)
    user = update.effective_user
    await db.upsert_user(user.id, user.username, user.first_name)

    t = await db.get_tournament(tournament_id)
    if not t or not t["registration_open"]:
        await query.answer("Регистрация закрыта.", show_alert=True)
        return

    ok = await db.register_participant(tournament_id, user.id)
    if ok:
        await query.answer("✅ Вы зарегистрированы!", show_alert=True)
    else:
        await query.answer("Вы уже зарегистрированы.", show_alert=True)

    # Refresh view
    context.args = []
    update.callback_query.data = f"tournament:view:{tournament_id}"
    await cb_tournament_view(update, context)


async def cb_reg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, _, tid = query.data.split(":")
    tournament_id = int(tid)
    user = update.effective_user

    t = await db.get_tournament(tournament_id)
    if not t or not t["registration_open"]:
        await query.answer("Регистрация закрыта.", show_alert=True)
        return

    await db.unregister_participant(tournament_id, user.id)
    await query.answer("❌ Регистрация отменена.", show_alert=True)

    update.callback_query.data = f"tournament:view:{tournament_id}"
    await cb_tournament_view(update, context)


# ─── Leaderboard ──────────────────────────────────────────────────────────────

async def cb_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    rows = await db.get_leaderboard()
    if not rows:
        text = "📊 <b>Лидерборд</b>\n\nПока нет данных."
    else:
        lines = ["📊 <b>Лидерборд</b>\n"]
        rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, row in enumerate(rows, start=1):
            rank = rank_emoji.get(i, f"{i}.")
            name = user_display(row)
            pts = row["points"]
            medals = (
                f"🥇×{row['wins']} " if row["wins"] else ""
            ) + (
                f"🥈×{row['seconds']} " if row["seconds"] else ""
            ) + (
                f"🥉×{row['thirds']}" if row["thirds"] else ""
            )
            lines.append(f"{rank} <b>{name}</b> — {pts} очк.  {medals.strip()}")
        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.back_to_main_kb(),
    )


# ─── Profile ──────────────────────────────────────────────────────────────────

async def cb_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    await db.upsert_user(user.id, user.username, user.first_name)

    results = await db.get_user_results(user.id)

    # Calculate total points
    total_points = sum(POINTS.get(r["place"], 0) for r in results)

    # Build medals row (scrollable via horizontal line of emojis)
    medals_parts = []
    for r in results:
        if r["place"] in MEDAL_EMOJI:
            medals_parts.append(f"{MEDAL_EMOJI[r['place']]}")
    medals_row = " ".join(medals_parts) if medals_parts else "—"

    # Build match history table
    if results:
        history_lines = ["<b>История матчей:</b>", ""]
        history_lines.append("<code>Турнир               Место</code>")
        history_lines.append("<code>─────────────────────────────</code>")
        for r in results:
            medal = MEDAL_EMOJI.get(r["place"], f"#{r['place']}")
            name = r["name"][:18].ljust(20)
            history_lines.append(f"<code>{name} {medal}</code>")
        history_text = "\n".join(history_lines)
    else:
        history_text = "<i>Матчей пока нет.</i>"

    name = user.first_name or user.username or f"id{user.id}"
    username_str = f"@{user.username}" if user.username else ""

    text = (
        f"👤 <b>{name}</b> {username_str}\n\n"
        f"🏅 <b>Медали:</b>\n{medals_row}\n\n"
        f"⭐ <b>Очки:</b> {total_points}\n\n"
        f"{history_text}"
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.back_to_main_kb(),
    )
