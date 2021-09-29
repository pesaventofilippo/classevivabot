from telepotpro.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton


def back():
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="◀️ Indietro", callback_data="settings_main")
            ]])


def lezioni(day=0):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Prima", callback_data=f"lezioni#{day-1}"),
                InlineKeyboardButton(text="Dopo ➡️", callback_data=f"lezioni#{day+1}")
            ]])


def settings_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔔 Ricevi notifiche", callback_data="settings_notifications"),
            InlineKeyboardButton(text="📲 Scegli notifiche", callback_data="settings_selectnews")
        ],
        [
            InlineKeyboardButton(text="😴 Mod. Non Disturbare", callback_data="settings_donotdisturb"),
            InlineKeyboardButton(text="🕑 Notifiche giornaliere", callback_data="settings_dailynotif")
        ],
        [
            InlineKeyboardButton(text="✔️ Chiudi", callback_data="settings_close")
        ]
    ])


def settings_notifications(active: bool=True):
    choices = {
        True: ["🔕 Disattiva", "no"],
        False: ["🔔 Attiva", "yes"]
    }
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=choices[active][0], callback_data=f"settings_notif_{choices[active][1]}"),
                InlineKeyboardButton(text="◀️ Indietro", callback_data="settings_main")
            ]])


def settings_selectnews():
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="📚 Didattica", callback_data="news_didattica"),
                InlineKeyboardButton(text="❗️ Note", callback_data="news_note")
            ], [
                InlineKeyboardButton(text="📝 Voti", callback_data="news_voti"),
                InlineKeyboardButton(text="📆 Agenda", callback_data="news_agenda")
            ], [
                InlineKeyboardButton(text="📩 Circolari", callback_data="news_circolari"),
                InlineKeyboardButton(text="◀️ Torna al menù", callback_data="settings_main")
            ]])


def settings_donotdisturb(active: bool=True):
    choices = {
        True: ["🔔 Suona", "no"],
        False: ["😴 Attiva", "yes"]
    }
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=choices[active][0], callback_data=f"settings_night_{choices[active][1]}"),
                InlineKeyboardButton(text="◀️ Indietro", callback_data="settings_main")
            ]])


def settings_dailynotif(active: bool=True):
    choices = {
        True: ["🔕 Disattiva", "no"],
        False: ["🔔 Attiva", "yes"]
    }
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🕙 -30 min.", callback_data="settings_daily_minus"),
                InlineKeyboardButton(text="🕙 +30 min.", callback_data="settings_daily_plus")
            ], [
                InlineKeyboardButton(text=choices[active][0], callback_data=f"settings_daily_{choices[active][1]}"),
                InlineKeyboardButton(text="◀️ Indietro", callback_data="settings_main")
            ]])


def logout():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✖️ Logout", callback_data="logout_yes"),
        InlineKeyboardButton(text="❌ Annulla", callback_data="logout_no")
    ]])


def mod_orario():
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="♻️ Modifica", callback_data="orario_mod"),
                InlineKeyboardButton(text="🗑 Elimina", callback_data="orario_del")
            ]])


def create_memo(today: int):
    days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    keyboard = [
        [
            InlineKeyboardButton(text="Domani", callback_data=f"memo_p1"),
            InlineKeyboardButton(text=days[(today+2)%6], callback_data=f"memo_p2"),
            InlineKeyboardButton(text=days[(today+3)%6], callback_data=f"memo_p3")
        ],
        [
            InlineKeyboardButton(text=days[(today+4)%6], callback_data=f"memo_p4"),
            InlineKeyboardButton(text=days[(today+5)%6], callback_data=f"memo_p5"),
            InlineKeyboardButton(text=days[(today+6)%6], callback_data=f"memo_p6"),
            InlineKeyboardButton(text=days[(today+7)%6] + " pross.", callback_data=f"memo_p7")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
