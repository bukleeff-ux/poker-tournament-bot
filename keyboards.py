from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Турниры", callback_data="menu:tournaments")],
        [InlineKeyboardButton("📊 Лидерборд", callback_data="menu:leaderboard")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="menu:profile")],
    ])


def tournaments_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Предстоящие", callback_data="tournaments:upcoming")],
        [InlineKeyboardButton("✅ Завершённые", callback_data="tournaments:completed")],
        [InlineKeyboardButton("◀️ Назад", callback_data="menu:main")],
    ])


def back_to_tournaments_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ К турнирам", callback_data="menu:tournaments")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")],
    ])


def back_to_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data="menu:main")],
    ])


def tournament_user_kb(tournament_id: int, is_registered: bool, reg_open: bool):
    buttons = []
    if reg_open:
        if is_registered:
            buttons.append([InlineKeyboardButton(
                "❌ Отменить регистрацию", callback_data=f"reg:cancel:{tournament_id}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                "✅ Зарегистрироваться", callback_data=f"reg:join:{tournament_id}"
            )])
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="tournaments:upcoming")])
    return InlineKeyboardMarkup(buttons)


# ─── Admin keyboards ──────────────────────────────────────────────────────────

def admin_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Создать турнир", callback_data="admin:create_tournament")],
        [InlineKeyboardButton("📋 Управление турнирами", callback_data="admin:list_tournaments")],
        [InlineKeyboardButton("👥 Участники", callback_data="admin:list_participants_select")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")],
    ])


def admin_tournament_kb(tournament_id: int, status: str, reg_open: bool):
    buttons = []
    if status != "completed":
        if reg_open:
            buttons.append([InlineKeyboardButton(
                "🔒 Закрыть регистрацию", callback_data=f"admin:reg_close:{tournament_id}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                "🔓 Открыть регистрацию", callback_data=f"admin:reg_open:{tournament_id}"
            )])
        if status == "upcoming":
            buttons.append([InlineKeyboardButton(
                "▶️ Начать турнир", callback_data=f"admin:start_tournament:{tournament_id}"
            )])
        if status == "active":
            buttons.append([InlineKeyboardButton(
                "🏁 Завершить турнир", callback_data=f"admin:finish_tournament:{tournament_id}"
            )])
    buttons.append([InlineKeyboardButton(
        "🥇 Назначить призёров", callback_data=f"admin:set_winners:{tournament_id}"
    )])
    buttons.append([InlineKeyboardButton(
        "👥 Участники", callback_data=f"admin:participants:{tournament_id}"
    )])
    buttons.append([InlineKeyboardButton(
        "🗑 Удалить турнир", callback_data=f"admin:delete_tournament:{tournament_id}"
    )])
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="admin:list_tournaments")])
    return InlineKeyboardMarkup(buttons)


def admin_tournaments_list_kb(tournaments):
    buttons = []
    for t in tournaments:
        status_icon = {"upcoming": "📅", "active": "⚡", "completed": "✅"}.get(t["status"], "❓")
        buttons.append([InlineKeyboardButton(
            f"{status_icon} {t['name']}", callback_data=f"admin:tournament:{t['id']}"
        )])
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="admin:menu")])
    return InlineKeyboardMarkup(buttons)


def admin_set_winner_place_kb(tournament_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥇 1 место", callback_data=f"admin:winner_place:{tournament_id}:1")],
        [InlineKeyboardButton("🥈 2 место", callback_data=f"admin:winner_place:{tournament_id}:2")],
        [InlineKeyboardButton("🥉 3 место", callback_data=f"admin:winner_place:{tournament_id}:3")],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"admin:tournament:{tournament_id}")],
    ])


def admin_pick_user_kb(tournament_id: int, place: int, participants):
    buttons = []
    for p in participants:
        name = p["first_name"] or p["username"] or str(p["tg_id"])
        buttons.append([InlineKeyboardButton(
            name, callback_data=f"admin:assign_winner:{tournament_id}:{place}:{p['tg_id']}"
        )])
    buttons.append([InlineKeyboardButton(
        "◀️ Назад", callback_data=f"admin:set_winners:{tournament_id}"
    )])
    return InlineKeyboardMarkup(buttons)


def admin_participants_kb(tournament_id: int, participants):
    buttons = []
    for p in participants:
        name = p["first_name"] or p["username"] or str(p["tg_id"])
        status = "🚫" if p["excluded"] else "✅"
        action = "include" if p["excluded"] else "exclude"
        buttons.append([InlineKeyboardButton(
            f"{status} {name}",
            callback_data=f"admin:{action}_participant:{tournament_id}:{p['tg_id']}"
        )])
    buttons.append([InlineKeyboardButton(
        "◀️ Назад", callback_data=f"admin:tournament:{tournament_id}"
    )])
    return InlineKeyboardMarkup(buttons)


def admin_select_tournament_for_participants_kb(tournaments):
    buttons = []
    for t in tournaments:
        buttons.append([InlineKeyboardButton(
            t["name"], callback_data=f"admin:participants:{t['id']}"
        )])
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="admin:menu")])
    return InlineKeyboardMarkup(buttons)


def confirm_delete_kb(tournament_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"admin:confirm_delete:{tournament_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"admin:tournament:{tournament_id}"),
        ]
    ])
