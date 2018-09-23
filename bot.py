import telepot
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from time import sleep
from datetime import datetime, timedelta
from tinydb import TinyDB, where
from modules.session import ClasseVivaAPI, AuthenticationFailedError
import modules.responser as resp
from modules.crypter import crypt, decrypt

bot = telepot.Bot(open('token.txt', 'r').readline().strip())
api = ClasseVivaAPI()
db = TinyDB('database.json')
inizioScuola = "2018/09/10"


def updateUserDatabase(user_id, username=None, password=None, status=None):
    password = crypt(password)
    if db.search(where('id') == user_id):
        if (username is None) and (password is None) and (status is None):
            return 0
        elif (username is None) and (password is None):
            db.update({'status': status}, where('id') == user_id)
        elif (username is None) and (status is None):
            db.update({'password': password}, where('id') == user_id)
        elif (password is None) and (status is None):
            db.update({'username': username}, where('id') == user_id)
        elif username is None:
            db.update({'password': password, 'status': status}, where('id') == user_id)
        elif password is None:
            db.update({'username': username, 'status': status}, where('id') == user_id)
        elif status is None:
            db.update({'username': username, 'password': password}, where('id') == user_id)
        else:
            db.update({'username': username, 'password': password, 'status': status}, where('id') == user_id)
    else:
        db.insert({'id': user_id, 'username': "", 'password': "", 'status': "normal"})


def isUserLogged(user_id):
    data = db.search(where('id') == user_id)[0]
    if (data['username'] == "") or (data['password'] == ""):
        return False
    else:
        return True


def runNotifications():
    pendingUsers = db.search(where('id') > 0)
    for user in pendingUsers:
        updateUserDatabase(user['id'], status="updating")
        api.login(user['username'], decrypt(user['password']))

        note = resp.parseNoteNew(api.note())
        if note != "":
            bot.sendMessage(user['id'], "❗️<b>Hai ricevuto nuove note:</b>{0}".format(note), parse_mode="HTML")

        api.logout()
        updateUserDatabase(user['id'], status="normal")


def rispondi(msg):
    msgType, chatType, chatId = telepot.glance(msg)
    text = msg['text']
    name = msg['from']['first_name']
    updateUserDatabase(chatId)
    status = db.search(where('id') == chatId)[0]['status']

    if status != "normal":
        if text == "/annulla":
            updateUserDatabase(chatId, status="normal")
            bot.sendMessage(chatId, "Comando annullato.")

        elif status == "login_0":
            updateUserDatabase(chatId, username=text, status="login_1")
            bot.sendMessage(chatId, "Ottimo. Adesso inviami la password.")

        elif status == "login_1":
            updateUserDatabase(chatId, password=text, status="normal")
            try:
                api.login(db.search(where('id') == chatId)[0]['username'], text)
                bot.sendMessage(chatId, "Fatto!")
                api.logout()
            except AuthenticationFailedError:
                bot.sendMessage(chatId, "Errore: Username o password non corretti.\n"
                                        "Premi /login per riprovare.")
                updateUserDatabase(chatId, "", "")

        elif status == "updating":
            bot.sendMessage(chatId, "😴 Sto aggiornando il tuo profilo, torna fra un minuto.")


    elif text == "/help":
        message = "Sono il bot di <b>ClasseViva</b>.\n" \
                  "Posso aiutarti a <b>navigare</b> nel registro e posso mandarti <b>notifiche</b>, se vuoi.\n\n" \
                  "<b>Lista dei comandi</b>:\n" \
                  "/start - Avvia il bot\n" \
                  "/help - Visualizza questo messaggio\n" \
                  "/login - Effettua il login\n" \
                  "/logout - Disconnettiti\n" \
                  "/agenda - Visualizza agenda (compiti e verifiche)\n" \
                  "/assenze - Visualizza assenze, ritardi e uscite anticipate\n" \
                  "/didattica - Visualizza la lista dei file in didattica\n" \
                  "/lezioni - Visualizza la lista delle lezioni\n" \
                  "/voti - Visualizza la lista dei voti\n" \
                  "/note - Visualizza la lista delle note\n" \
                  "/info - Visualizza le tue info utente\n" \
                  "/prof - Visualizza la lista delle materie e dei prof\n" \
                  "\n\n" \
                  "<b>Notifiche</b>: ogni ora, il bot ti invierà un messagio se ti sono arrivate nuove note."
        bot.sendMessage(chatId, message, parse_mode="HTML")


    elif isUserLogged(chatId):
        api.login(db.search(where('id') == chatId)[0]['username'], decrypt(db.search(where('id') == chatId)[0]['password']))

        if text == "/start":
            bot.sendMessage(chatId, "Bentornato, <b>{0}</b>!\n"
                                    "Cosa posso fare per te?".format(name), parse_mode="HTML")

        elif text == "/login":
            bot.sendMessage(chatId, "Sei già loggato.\n"
                                    "Premi /logout per uscire.")

        elif text == "/logout":
            updateUserDatabase(chatId, "", "", "normal")
            bot.sendMessage(chatId, "Fatto, sei stato disconnesso!\n"
                                    "Premi /login per entrare di nuovo.\n\n"
                                    "Premi /help se serve aiuto.")

        elif text == "/didattica":
            bot.sendChatAction(chatId, "typing")
            data = resp.parseDidattica(api.didattica())
            bot.sendMessage(chatId, "📚 <b>Files caricati in didadttica</b>:{0}".format(data), parse_mode="HTML")

        elif text == "/info":
            bot.sendChatAction(chatId, "typing")
            data = resp.parseInfo(api.info())
            bot.sendMessage(chatId, "ℹ️ <b>Ecco le tue info</b>:\n\n"
                                    "{0}".format(data), parse_mode="HTML")

        elif text == "/prof":
            bot.sendChatAction(chatId, "typing")
            data = resp.parseMaterie(api.materie())
            bot.sendMessage(chatId, "📚 <b>Lista materie e prof</b>:{0}".format(data), parse_mode="HTML")

        elif text == "/note":
            bot.sendChatAction(chatId, "typing")
            data = resp.parseNote(api.note())
            bot.sendMessage(chatId, "❗️<b>Le tue note:</b>{0}".format(data), parse_mode="HTML")

        elif text == "/voti":
            bot.sendChatAction(chatId, "typing")
            data = resp.parseVoti(api.voti())
            bot.sendMessage(chatId, "📝 <b>I tuoi voti</b>:\n{0}".format(data), parse_mode="HTML")

        elif text == "/assenze":
            bot.sendChatAction(chatId, "typing")
            data = resp.parseAssenze(api.assenze(inizioScuola.replace("/", "")))
            bot.sendMessage(chatId, "{0}".format(data), parse_mode="HTML")

        elif text == "/agenda":
            bot.sendChatAction(chatId, "typing")
            data = resp.parseAgenda(api.agenda(14))
            bot.sendMessage(chatId, "📆 <b>Agenda compiti delle prossime 2 settimane</b>:\n"
                                    "{0}".format(data), parse_mode="HTML")

        elif text == "/lezioni":
            bot.sendChatAction(chatId, "typing")
            data = resp.parseLezioni(api.lezioni())
            message_id = bot.sendMessage(chatId, "📚 <b>Lezioni di oggi</b>:\n\n"
                                              "{0}".format(data), parse_mode="HTML", reply_markup=None)['message_id']
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Prima", callback_data="lezioni_prima#{0}#0".format(message_id)),
                InlineKeyboardButton(text="Dopo ➡️", callback_data="lezioni_dopo#{0}#0".format(message_id))
            ]])
            bot.editMessageReplyMarkup((chatId, message_id), reply_markup=keyboard)

        else:
            bot.sendMessage(chatId, "Non ho capito...\n"
                                    "Serve aiuto? Premi /help")

        api.logout()


    else:
        if text == "/login":
            updateUserDatabase(chatId, status="login_0")
            bot.sendMessage(chatId, "Per favore, inviami il tuo <b>username</b> (quello che usi per accedere al registro).\n"
                                    "Usa /annulla se serve.", parse_mode="HTML")

        else:
            bot.sendMessage(chatId, "Benvenuto, <b>{0}</b>!\n"
                                    "Per favore, premi /login per utilizzarmi.\n\n"
                                    "Premi /help se serve aiuto.".format(name), parse_mode="HTML")


def button_press(msg):
    query_id, fromId, query_data = telepot.glance(msg, flavor="callback_query")
    query_split = query_data.split("#")
    message_id = int(query_split[1])
    button = query_split[0]
    api.login(db.search(where('id') == fromId)[0]['username'], decrypt(db.search(where('id') == fromId)[0]['password']))

    if button == "lezioni_prima":
        selectedDay = int(query_split[2]) - 1
        dateformat = (datetime.now() + timedelta(days=selectedDay)).strftime("%d/%m/%Y")
        data = resp.parseLezioni(api.lezioni(selectedDay))
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Prima", callback_data="lezioni_prima#{0}#{1}".format(message_id, selectedDay)),
            InlineKeyboardButton(text="Dopo ➡️", callback_data="lezioni_dopo#{0}#{1}".format(message_id, selectedDay))
        ]])
        bot.editMessageText((fromId, message_id), "📚 <b>Lezioni del {0}</b>:\n\n"
                                                  "{1}".format(dateformat, data), parse_mode="HTML", reply_markup=keyboard)

    elif button == "lezioni_dopo":
        selectedDay = int(query_split[2]) + 1
        dateformat = (datetime.now() + timedelta(days=selectedDay)).strftime("%d/%m/%Y")
        data = resp.parseLezioni(api.lezioni(selectedDay))
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Prima", callback_data="lezioni_prima#{0}#{1}".format(message_id, selectedDay)),
            InlineKeyboardButton(text="Dopo ➡️", callback_data="lezioni_dopo#{0}#{1}".format(message_id, selectedDay))
        ]])
        bot.editMessageText((fromId, message_id), "📚 <b>Lezioni del {0}</b>:\n\n"
                                                  "{1}".format(dateformat, data), parse_mode="HTML", reply_markup=keyboard)

    api.logout()


bot.message_loop({'chat': rispondi, 'callback_query': button_press})
print("Bot started...")
while True:
    sleep(60)
    if datetime.now().strftime("%m") == "00":
        runNotifications()