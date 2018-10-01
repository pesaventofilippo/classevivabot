import telepot
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from time import sleep
from datetime import datetime, timedelta
from tinydb import TinyDB, where
from modules.session import ClasseVivaAPI, AuthenticationFailedError
import modules.responser as resp
from modules.crypter import crypt, decrypt

try:
    f = open('token.txt', 'r')
    token = f.readline().strip()
    f.close()
except FileNotFoundError:
    token = input("File 'token.txt' not found. Please insert the bot Token: ")
    f = open('token.txt', 'w')
    f.write(token)
    f.close()

bot = telepot.Bot(token)
api = ClasseVivaAPI()
db = TinyDB('database.json')
data_db = TinyDB('data.json')
inizioScuola = "2018/09/10"


def updateUserDatabase(user_id, username=None, password=None, status=None):
    password = crypt(password)
    if db.search(where('id') == user_id):
        if username is not None:
            db.update({'username': username}, where('id') == user_id)
        elif password is not None:
            db.update({'password': password}, where('id') == user_id)
        elif status is not None:
            db.update({'status': status}, where('id') == user_id)
    else:
        db.insert({'id': user_id, 'username': "", 'password': "", 'status': "normal"})


def updateDataDatabase(user_id, didattica=None, note=None, voti=None, assenze=None, agenda=None):
    if data_db.search(where('id') == user_id):
        if didattica is not None:
            data_db.update({'didattica': didattica}, where('id') == user_id)
        elif note is not None:
            data_db.update({'note': note}, where('id') == user_id)
        elif voti is not None:
            data_db.update({'voti': voti}, where('id') == user_id)
        elif assenze is not None:
            data_db.update({'assenze': assenze}, where('id') == user_id)
        elif agenda is not None:
            data_db.update({'agenda': agenda}, where('id') == user_id)
    else:
        data_db.insert({'id': user_id, 'didattica': {}, 'note': {}, 'voti': {}, 'assenze': {}, 'agenda': {}})


def isUserLogged(user_id):
    if db.search(where('id') == user_id)[0]['password'] == "":
        return False
    else:
        return True


def runNotifications():
    pendingUsers = db.search(where('password') != "")
    for user in pendingUsers:
        updateUserDatabase(user['id'], status="updating")
        api.login(user['username'], decrypt(user['password']))
        userdata = data_db.search(where('id') == user['id'])[0]

        # newDidattica = api.didattica()
        newNote = api.note()
        newVoti = api.voti()
        newAssenze = api.assenze(inizioScuola.replace("/", ""))
        newAgenda = api.agenda(14)

        # oldDidattica = userdata['didattica']
        oldNote = userdata['note']
        oldVoti = userdata['voti']
        oldAssenze = userdata['assenze']
        oldAgenda = userdata['agenda']

        # WIP dataDidattica = resp.parseNewDidattica(oldDidattica, newDidattica)
        dataNote = resp.parseNewNote(oldNote, newNote)
        dataVoti = resp.parseNewVoti(oldVoti, newVoti)
        dataAssenze = resp.parseNewAssenze(oldAssenze, newAssenze)
        dataAgenda = resp.parseNewAgenda(oldAgenda, newAgenda)
        
        message = ""
        
        if dataNote is not None:
            message += "❗️<b>Nuove note</b>{0}\n\n\n".format(dataNote)
        
        if dataVoti is not None:
            message += "📝 <b>Nuovi voti</b>\n{0}\n\n\n".format(dataVoti)
        
        if dataAssenze is not None:
            message += "🏫 <b>Nuove assenze</b>{0}\n\n\n".format(dataAssenze)
        
        if dataAgenda is not None:
            message += "📆 <b>Nuovi impegni in agenda</b>\n{0}".format(dataAgenda)
        
        
        if message != "":
            bot.sendMessage(user['id'], "🔔 <b>Hai nuove notifiche!</b>\n\n"+message, parse_mode="HTML")
        

        updateDataDatabase(user['id'], newDidattica, newNote, newVoti, newAssenze, newAgenda)
        api.logout()
        updateUserDatabase(user['id'], status="normal")


def rispondi(msg):
    msgType, chatType, chatId = telepot.glance(msg)
    text = msg['text']
    name = msg['from']['first_name']
    updateUserDatabase(chatId)
    updateDataDatabase(chatId)
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
                updateUserDatabase(chatId, username="", password="")

        elif status == "updating":
            bot.sendMessage(chatId, "😴 Sto aggiornando il tuo profilo, aspetta un attimo.")


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
            updateUserDatabase(chatId, username="", password="", status="normal")
            updateDataDatabase(chatId, {}, {}, {}, {}, {})
            bot.sendMessage(chatId, "Fatto, sei stato disconnesso!\n"
                                    "Premi /login per entrare di nuovo.\n\n"
                                    "Premi /help se serve aiuto.")

        elif text == "/didattica":
            bot.sendChatAction(chatId, "typing")
            response = api.didattica()
            updateDataDatabase(chatId, didattica=response)
            data = resp.parseDidattica(response)
            bot.sendMessage(chatId, "📚 <b>Files caricati in didadttica</b>:{0}".format(data), parse_mode="HTML")

        elif text == "/info":
            bot.sendChatAction(chatId, "typing")
            data = resp.parseDidattica(api.info())
            bot.sendMessage(chatId, "ℹ️ <b>Ecco le tue info</b>:\n\n"
                                    "{0}".format(data), parse_mode="HTML")

        elif text == "/prof":
            bot.sendChatAction(chatId, "typing")
            data = resp.parseMaterie(api.materie())
            bot.sendMessage(chatId, "📚 <b>Lista materie e prof</b>:{0}".format(data), parse_mode="HTML")

        elif text == "/note":
            bot.sendChatAction(chatId, "typing")
            response = api.note()
            updateDataDatabase(chatId, note=response)
            data = resp.parseNote(response)
            bot.sendMessage(chatId, "❗️<b>Le tue note:</b>{0}".format(data), parse_mode="HTML")

        elif text == "/voti":
            bot.sendChatAction(chatId, "typing")
            response = api.voti()
            updateDataDatabase(chatId, voti=response)
            data = resp.parseVoti(response)
            bot.sendMessage(chatId, "📝 <b>I tuoi voti</b>:\n{0}".format(data), parse_mode="HTML")

        elif text == "/assenze":
            bot.sendChatAction(chatId, "typing")
            response = api.assenze(inizioScuola.replace("/", ""))
            updateDataDatabase(chatId, assenze=response)
            data = resp.parseAssenze(response)
            bot.sendMessage(chatId, "{0}".format(data), parse_mode="HTML")

        elif text == "/agenda":
            bot.sendChatAction(chatId, "typing")
            response = api.agenda(14)
            updateDataDatabase(chatId, agenda=response)
            data = resp.parseAgenda(response)
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
    if datetime.now().minute == 0:
        runNotifications()