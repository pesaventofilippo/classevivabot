from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton


def back(msgid):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="◀️ Indietro", callback_data="settings_main#{0}".format(msgid))
            ]])


def payments():
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔷 PayPal", url="cut.pesaventofilippo.com/donacvvbot")
            ]])


def lezioni(msgid, day=0):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Prima", callback_data="lezioni_prima#{0}#{1}".format(msgid, day)),
                InlineKeyboardButton(text="Dopo ➡️", callback_data="lezioni_dopo#{0}#{1}".format(msgid, day))
            ]])


def settings_menu(msgid):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔔 Ricevi notifiche", callback_data="settings_notifications#{0}".format(msgid))
            ], [
                InlineKeyboardButton(text="📲 Scegli notifiche", callback_data="settings_selectnews#{0}".format(msgid))
            ], [
                InlineKeyboardButton(text="😴 Mod. Non Disturbare", callback_data="settings_donotdisturb#{0}".format(msgid))
            ], [
                InlineKeyboardButton(text="🕑 Notifiche giornaliere", callback_data="settings_dailynotif#{0}".format(msgid))
            ]])


def settings_notifications(msgid):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔔 Attiva", callback_data="settings_notif_yes#{0}".format(msgid)),
                InlineKeyboardButton(text="🔕 Disattiva", callback_data="settings_notif_no#{0}".format(msgid))
            ], [
                InlineKeyboardButton(text="◀️ Torna al menù", callback_data="settings_main#{0}".format(msgid))
            ]])


def settings_selectnews(msgid):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="📚 Didattica", callback_data="news_didattica#{0}".format(msgid)),
                InlineKeyboardButton(text="❗️ Note", callback_data="news_note#{0}".format(msgid))
            ], [
                InlineKeyboardButton(text="📝 Voti", callback_data="news_voti#{0}".format(msgid)),
                InlineKeyboardButton(text="📆 Agenda", callback_data="news_agenda#{0}".format(msgid))
            ], [
                InlineKeyboardButton(text="📩 Circolari", callback_data="news_circolari#{0}".format(msgid)),
                InlineKeyboardButton(text="◀️ Torna al menù", callback_data="settings_main#{0}".format(msgid))
            ]])


def settings_donotdisturb(msgid):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="😴 Attiva", callback_data="settings_night_yes#{0}".format(msgid)),
                InlineKeyboardButton(text="🔔 Suona", callback_data="settings_night_no#{0}".format(msgid))
            ], [
                InlineKeyboardButton(text="◀️ Torna al menù", callback_data="settings_main#{0}".format(msgid))
            ]])


def settings_dailynotif(msgid):
    return InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔔 Attiva", callback_data="settings_daily_yes#{0}".format(msgid)),
                InlineKeyboardButton(text="🔕 Disattiva", callback_data="settings_daily_no#{0}".format(msgid))
            ], [
                InlineKeyboardButton(text="🕙 -30 min.", callback_data="settings_daily_minus#{0}".format(msgid)),
                InlineKeyboardButton(text="🕙 +30 min.", callback_data="settings_daily_plus#{0}".format(msgid))
            ], [
                InlineKeyboardButton(text="◀️ Torna al menù", callback_data="settings_main#{0}".format(msgid))
            ]])


def logout(msgid):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✖️ Logout", callback_data="logout_yes#{0}".format(msgid)),
        InlineKeyboardButton(text="❌ Annulla", callback_data="logout_no#{0}".format(msgid))
    ]])
