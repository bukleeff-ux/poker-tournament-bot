from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

import database as db
import keyboards as kb
from config import ADMIN_IDS, MEDAL_EMOJI

# Conversation states
(
    CREATE_TOURNAMENT_NAME,
    CREATE_TOURNAMENT_DATE,
) = range(2)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def require_admin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not is_admin(user.id):
            if update.callback_query:
                await update.callback_query.answer()
            return
        return await func(update, context)
    return wrapper


def user_display(row) -> str:
    return row["first_name"] or row["username"] or f"id{row['tg_id']}"


# ─── /admin command ───────────────────────────────────────────────────────────

@require_admin
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙️ <b>Панель администратора</b>",
        parse_mode="HTML",
        reply_markup=kb.admin_menu_kb(),
    )


# ─── Admin menu callback ──────────────────────────────────────────────────────

@require_admin
async def cb_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚙️ <b>Панель администратора</b>",
        parse_mode="HTML",
        reply_markup=kb.admin_menu_kb(),
    )


# ─── Create tournament (ConversationHandler) ──────────────────────────────────

@require_admin
async def cb_create_tournament_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "➕ <b>Создание турнира</b>\n\nВведите название турнира:",
        parse_mode="HTML",
    )
    return CREATE_TOURNAMENT_NAME


async def create_tournament_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data["new_tournament_name"] = update.message.text.strip()
    await update.message.reply_text(
        "📅 Введите дату турнира (например: <code>25.12.2024</code>) или /skip чтобы пропустить:",
        parse_mode="HTML",
    )
    return CREATE_TOURNAMENT_DATE


async def create_tournament_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    date = update.message.text.strip()
    name = context.user_data.pop("new_tournament_name", "Без названия")
    tid = await db.create_tournament(name, date)
    await update.message.reply_text(
        f"✅ Турнир <b>{name}</b> (#{tid}) создан!",
        parse_mode="HTML",
        reply_markup=kb.admin_menu_kb(),
    )
    return ConversationHandler.END


async def create_tournament_skip_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    name = context.user_data.pop("new_tournament_name", "Без названия")
    tid = await db.create_tournament(name)
    await update.message.reply_text(
        f"✅ Турнир <b>{name}</b> (#{tid}) создан!",
        parse_mode="HTML",
        reply_markup=kb.admin_menu_kb(),
    )
    return ConversationHandler.END


async def create_tournament_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_tournament_name", None)
    await update.message.reply_text(
        "❌ Создание турнира отменено.",
        reply_markup=kb.admin_menu_kb(),
    )
    return ConversationHandler.END


def get_create_tournament_conv():
    return ConversationHandler(
        entry_points=[],  # Triggered via callback, added manually
        states={
            CREATE_TOURNAMENT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_tournament_name),
                CommandHandler("cancel", create_tournament_cancel),
            ],
            CREATE_TOURNAMENT_DATE: [
                CommandHandler("skip", create_tournament_skip_date),
                CommandHandler("cancel", create_tournament_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_tournament_date),
            ],
        },
        fallbacks=[CommandHandler("cancel", create_tournament_cancel)],
        allow_reentry=True,
    )


# ─── List tournaments ─────────────────────────────────────────────────────────

@require_admin
async def cb_admin_list_tournaments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tournaments = await db.get_all_tournaments()
    if not tournaments:
        await query.edit_message_text(
            "📋 Турниров пока нет.",
            reply_markup=kb.admin_menu_kb(),
        )
        return
    await query.edit_message_text(
        "📋 <b>Все турниры</b>\n\nВыберите турнир:",
        parse_mode="HTML",
        reply_markup=kb.admin_tournaments_list_kb(tournaments),
    )


@require_admin
async def cb_admin_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    tournament_id = int(parts[2])
    t = await db.get_tournament(tournament_id)
    if not t:
        await query.edit_message_text("Турнир не найден.", reply_markup=kb.admin_menu_kb())
        return

    results = await db.get_results(tournament_id)
    participants = await db.get_participants(tournament_id)
    active_count = sum(1 for p in participants if not p["excluded"])

    status_map = {"upcoming": "📅 Ожидание", "active": "⚡ Идёт", "completed": "✅ Завершён"}
    date_str = f"\n📅 Дата: {t['date']}" if t["date"] else ""
    reg_str = "🔓 Открыта" if t["registration_open"] else "🔒 Закрыта"

    prizes_lines = []
    for r in results:
        medal = MEDAL_EMOJI.get(r["place"], f"#{r['place']}")
        prizes_lines.append(f"  {medal} {user_display(r)}")
    prizes_text = "\n".join(prizes_lines) if prizes_lines else "  —"

    text = (
        f"🏆 <b>{t['name']}</b> (#{t['id']})\n"
        f"Статус: {status_map.get(t['status'], t['status'])}\n"
        f"Регистрация: {reg_str}{date_str}\n"
        f"👥 Участников: {active_count}\n\n"
        f"🏅 Призёры:\n{prizes_text}"
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.admin_tournament_kb(tournament_id, t["status"], bool(t["registration_open"])),
    )


# ─── Registration open/close ──────────────────────────────────────────────────

@require_admin
async def cb_admin_reg_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    tournament_id = int(parts[2])
    await db.update_registration(tournament_id, True)
    await query.answer("✅ Регистрация открыта!", show_alert=True)
    query.data = f"admin:tournament:{tournament_id}"
    await cb_admin_tournament(update, context)


@require_admin
async def cb_admin_reg_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    tournament_id = int(parts[2])
    await db.update_registration(tournament_id, False)
    await query.answer("🔒 Регистрация закрыта.", show_alert=True)
    query.data = f"admin:tournament:{tournament_id}"
    await cb_admin_tournament(update, context)


# ─── Start / finish tournament ────────────────────────────────────────────────

@require_admin
async def cb_admin_start_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    tournament_id = int(parts[2])
    await db.update_tournament_status(tournament_id, "active")
    await db.update_registration(tournament_id, False)
    await query.answer("⚡ Турнир начался!", show_alert=True)
    query.data = f"admin:tournament:{tournament_id}"
    await cb_admin_tournament(update, context)


@require_admin
async def cb_admin_finish_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    tournament_id = int(parts[2])
    await db.update_tournament_status(tournament_id, "completed")
    await query.answer("✅ Турнир завершён!", show_alert=True)
    query.data = f"admin:tournament:{tournament_id}"
    await cb_admin_tournament(update, context)


# ─── Delete tournament ────────────────────────────────────────────────────────

@require_admin
async def cb_admin_delete_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    tournament_id = int(parts[2])
    t = await db.get_tournament(tournament_id)
    if not t:
        await query.edit_message_text("Турнир не найден.")
        return
    await query.edit_message_text(
        f"⚠️ Удалить турнир <b>{t['name']}</b>?\n\nВсе результаты и участники будут удалены.",
        parse_mode="HTML",
        reply_markup=kb.confirm_delete_kb(tournament_id),
    )


@require_admin
async def cb_admin_confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    tournament_id = int(parts[2])
    await db.delete_tournament(tournament_id)
    await query.edit_message_text(
        "🗑 Турнир удалён.",
        reply_markup=kb.admin_menu_kb(),
    )


# ─── Set winners ──────────────────────────────────────────────────────────────

@require_admin
async def cb_admin_set_winners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    tournament_id = int(parts[2])
    await query.edit_message_text(
        "🏅 Выберите место для назначения призёра:",
        reply_markup=kb.admin_set_winner_place_kb(tournament_id),
    )


@require_admin
async def cb_admin_winner_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    # admin:winner_place:{tid}:{place}
    tournament_id = int(parts[2])
    place = int(parts[3])

    participants = await db.get_participants(tournament_id)
    active = [p for p in participants if not p["excluded"]]
    if not active:
        await query.answer("Нет участников в турнире.", show_alert=True)
        return

    place_labels = {1: "🥇 1 место", 2: "🥈 2 место", 3: "🥉 3 место"}
    await query.edit_message_text(
        f"Выберите участника на {place_labels.get(place, str(place))}:",
        reply_markup=kb.admin_pick_user_kb(tournament_id, place, active),
    )


@require_admin
async def cb_admin_assign_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    # admin:assign_winner:{tid}:{place}:{user_id}
    tournament_id = int(parts[2])
    place = int(parts[3])
    winner_id = int(parts[4])

    await db.set_result(tournament_id, winner_id, place)
    user = await db.get_user(winner_id)
    name = user_display(user) if user else str(winner_id)

    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(place, "🏅")
    await query.answer(f"{medal} {name} — {place} место!", show_alert=True)

    query.data = f"admin:tournament:{tournament_id}"
    await cb_admin_tournament(update, context)


# ─── Participants management ──────────────────────────────────────────────────

@require_admin
async def cb_admin_list_participants_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tournaments = await db.get_all_tournaments()
    if not tournaments:
        await query.edit_message_text("Турниров нет.", reply_markup=kb.admin_menu_kb())
        return
    await query.edit_message_text(
        "👥 Выберите турнир для управления участниками:",
        reply_markup=kb.admin_select_tournament_for_participants_kb(tournaments),
    )


@require_admin
async def cb_admin_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    tournament_id = int(parts[2])

    t = await db.get_tournament(tournament_id)
    participants = await db.get_participants(tournament_id)

    if not participants:
        await query.edit_message_text(
            f"👥 <b>{t['name']}</b>\n\nУчастников пока нет.",
            parse_mode="HTML",
            reply_markup=kb.admin_tournament_kb(tournament_id, t["status"], bool(t["registration_open"])),
        )
        return

    await query.edit_message_text(
        f"👥 <b>{t['name']}</b> — участники\n\n✅ — активен   🚫 — исключён",
        parse_mode="HTML",
        reply_markup=kb.admin_participants_kb(tournament_id, participants),
    )


@require_admin
async def cb_admin_exclude_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    # admin:exclude_participant:{tid}:{uid}
    tournament_id = int(parts[2])
    user_id = int(parts[3])
    await db.exclude_participant(tournament_id, user_id)
    query.data = f"admin:participants:{tournament_id}"
    await cb_admin_participants(update, context)


@require_admin
async def cb_admin_include_participant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    # admin:include_participant:{tid}:{uid}
    tournament_id = int(parts[2])
    user_id = int(parts[3])
    await db.include_participant(tournament_id, user_id)
    query.data = f"admin:participants:{tournament_id}"
    await cb_admin_participants(update, context)
