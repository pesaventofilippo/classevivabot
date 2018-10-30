import telepot
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from telepot.exception import TelegramError, BotWasBlockedError
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
data_db = TinyDB('userdata.json')
inizioScuola = "2018/09/10"
updatesStartHour = 7
updatesStopHour = 21

botStatus = "running"


def updateUserDatabase(user_id, username=None, password=None, status=None):
    password = crypt(password)
    if db.search(where('id') == user_id):
        if username is not None:
            db.update({'username': username}, where('id') == user_id)
        if password is not None:
            db.update({'password': password}, where('id') == user_id)
        if status is not None:
            db.update({'status': status}, where('id') == user_id)
    else:
        db.insert({'id': user_id, 'username': "", 'password': "", 'status': "normal"})


def updateDataDatabase(user_id, didattica=None, note=None, voti=None, assenze=None, agenda=None):
    if data_db.search(where('id') == user_id):
        if didattica is not None:
            data_db.update({'didattica': didattica}, where('id') == user_id)
        if note is not None:
            data_db.update({'note': note}, where('id') == user_id)
        if voti is not None:
            data_db.update({'voti': voti}, where('id') == user_id)
        if assenze is not None:
            data_db.update({'assenze': assenze}, where('id') == user_id)
        if agenda is not None:
            data_db.update({'agenda': agenda}, where('id') == user_id)
    else:
        data_db.insert({'id': user_id, 'didattica': {}, 'note': {}, 'voti': {}, 'assenze': {}, 'agenda': {}})


def isUserLogged(user_id):
    try:
        if db.search(where('id') == user_id)[0]['password'] == "":
            return False
        else:
            return True
    except IndexError:
        return False


def runNotifications():
    pendingUsers = db.search(where('password') != "")
    for user in pendingUsers:
        try:
            api.login(user['username'], decrypt(user['password']))
            userdata = data_db.search(where('id') == user['id'])[0]

            newDidattica = api.didattica()
            newNote = api.note()
            newVoti = api.voti()
            newAssenze = api.assenze(inizioScuola.replace("/", ""))
            newAgenda = api.agenda(14)

            # oldDidattica = userdata['didattica']
            oldNote = userdata['note']
            oldVoti = userdata['voti']
            oldAssenze = userdata['assenze']
            oldAgenda = userdata['agenda']

            # dataDidattica = resp.parseNewDidattica(oldDidattica, newDidattica)
            dataNote = resp.parseNewNote(oldNote, newNote)
            dataVoti = resp.parseNewVoti(oldVoti, newVoti)
            dataAssenze = resp.parseNewAssenze(oldAssenze, newAssenze)
            dataAgenda = resp.parseNewAgenda(oldAgenda, newAgenda)

            firstMessage = True

            if dataNote is not None:
                header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                bot.sendMessage(user['id'], header + "❗️<b>Nuove note</b>{0}\n\n\n".format(dataNote), parse_mode="HTML")
                firstMessage = False

            if dataVoti is not None:
                header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                bot.sendMessage(user['id'], header + "📝 <b>Nuovi voti</b>\n{0}\n\n\n".format(dataVoti), parse_mode="HTML")
                firstMessage = False

            if dataAssenze is not None:
                header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                bot.sendMessage(user['id'], header + "🏫 <b>Nuove assenze</b>{0}\n\n\n".format(dataAssenze), parse_mode="HTML")
                firstMessage = False

            if dataAgenda is not None:
                header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                bot.sendMessage(user['id'], header + "📆 <b>Nuovi impegni in agenda</b>\n{0}".format(dataAgenda), parse_mode="HTML")

            updateDataDatabase(user['id'], newDidattica, newNote, newVoti, newAssenze, newAgenda)
            api.logout()

        except AuthenticationFailedError:
            updateUserDatabase(user['id'], username="", password="")
            try:
                bot.sendMessage(user['id'], "😯 Le tue credenziali di accesso sono cambiate o sono errate.\n"
                                            "Effettua nuovamente il /login per favore.")
            except (TelegramError, BotWasBlockedError):
                pass

        except (TelegramError, BotWasBlockedError):
            pass

        except IndexError:
            updateDataDatabase(user['id'])

        except KeyError:
            updateUserDatabase(user['id'], username="", password="")
            try:
                bot.sendMessage(user['id'], "😯 Le tue credenziali di accesso sono cambiate o sono errate.\n"
                                            "Effettua nuovamente il /login per favore.")
            except (TelegramError, BotWasBlockedError):
                pass



def reply(msg):
    msgType, chatType, chatId = telepot.glance(msg)
    updateUserDatabase(chatId)
    updateDataDatabase(chatId)
    text = msg['text']
    name = msg['from']['first_name']
    status = db.search(where('id') == chatId)[0]['status']

    if botStatus != "running":
        bot.sendMessage(chatId, "😴 Al momento sono impegnato, per favore riprova fra qualche minuto.")
        return 0


    if status != "normal":
        if text == "/annulla":
            updateUserDatabase(chatId, status="normal")
            bot.sendMessage(chatId, "Comando annullato!")

        elif status == "login_0":
            updateUserDatabase(chatId, username=text, status="login_1")
            bot.sendMessage(chatId, "👍 Ottimo. Adesso inviami la password.\n"
                                    "Ricorda che la password viene salvata solo per te e viene criptata, nessuno potrà leggerla.")

        elif status == "login_1":
            updateUserDatabase(chatId, password=text, status="normal")
            try:
                api.login(db.search(where('id') == chatId)[0]['username'], text)
                bot.sendMessage(chatId, "Fatto 😊\n"
                                        "Premi /help per vedere la lista dei comandi disponibili.")
                api.logout()
            except AuthenticationFailedError:
                updateUserDatabase(chatId, username="", password="")
                bot.sendMessage(chatId, "😯 Le tue credenziali di accesso sono errate.\n"
                                        "Effettua nuovamente il /login per favore.")


    elif text == "/help":
        message = "Ciao, sono il bot di <b>ClasseViva</b>!\n" \
                  "Posso aiutarti a <b>navigare</b> nel registro e posso mandarti <b>notifiche</b> quando hai nuovi avvisi.\n\n" \
                  "<b>Lista dei comandi</b>:\n\n" \
                  "/start - Avvia il bot\n\n" \
                  "/help - Visualizza questo messaggio\n\n" \
                  "/login - Effettua il login\n\n" \
                  "/logout - Disconnettiti\n\n" \
                  "/aggiorna - Aggiorna manualmente tutti i dati, per controllare se ci sono nuovi avvisi.\n" \
                                "Oppure, puoi lasciarlo fare a me, ogni ora :)\n\n" \
                  "/agenda - Visualizza agenda (compiti e verifiche)\n\n" \
                  "/assenze - Visualizza assenze, ritardi e uscite anticipate\n\n" \
                  "/didattica - Visualizza la lista dei file in didattica\n\n" \
                  "/lezioni - Visualizza la lista delle lezioni\n\n" \
                  "/voti - Visualizza la lista dei voti\n\n" \
                  "/note - Visualizza la lista delle note\n\n" \
                  "/info - Visualizza le tue info utente\n\n" \
                  "/prof - Visualizza la lista delle materie e dei prof\n\n" \
                  "\n" \
                  "<b>Notifiche</b>: ogni ora, ti invierò un messagio se ti sono arrivati nuovi voti, note, compiti o assenze."
        bot.sendMessage(chatId, message, parse_mode="HTML")

    elif isUserLogged(chatId):
        try:
            api.login(db.search(where('id') == chatId)[0]['username'], decrypt(db.search(where('id') == chatId)[0]['password']))
        except AuthenticationFailedError:
            updateUserDatabase(chatId, username="", password="")
            bot.sendMessage(chatId, "😯 Le tue credenziali di accesso sono cambiate o sono errate.\n"
                                    "Esegui nuovamente il /login per favore.")
            return 0

        if text == "/start":
            bot.sendMessage(chatId, "Bentornato, <b>{0}</b>!\n"
                                    "Cosa posso fare per te? 😊".format(name), parse_mode="HTML")

        elif text == "/login":
            bot.sendMessage(chatId, "Sei già loggato.\n"
                                    "Premi /logout per uscire.")

        elif text == "/logout":
            updateUserDatabase(chatId, username="", password="", status="normal")
            updateDataDatabase(chatId, {}, {}, {}, {}, {})
            bot.sendMessage(chatId, "😯 Fatto, sei stato disconnesso!\n"
                                    "Premi /login per entrare di nuovo.\n\n"
                                    "Premi /help se serve aiuto.")

        elif text == "/didattica":
            sent = bot.sendMessage(chatId, "Carico...\nAspetta qualche secondo")
            response = api.didattica()
            updateDataDatabase(chatId, didattica=response)
            data = resp.parseDidattica(response)
            bot.editMessageText((chatId, sent['message_id']),
                                "📚 <b>Files caricati in didadttica</b>:{0}".format(data), parse_mode="HTML")

        elif text == "/info":
            sent = bot.sendMessage(chatId, "Carico...\nAspetta qualche secondo")
            data = resp.parseInfo(api.info())
            bot.editMessageText((chatId, sent['message_id']), "ℹ️ <b>Ecco le tue info</b>:\n\n"
                                    "{0}".format(data), parse_mode="HTML")

        elif text == "/prof":
            sent = bot.sendMessage(chatId, "Carico...\nAspetta qualche secondo")
            data = resp.parseMaterie(api.materie())
            bot.editMessageText((chatId, sent['message_id']),
                            "📚 <b>Lista materie e prof</b>:{0}".format(data), parse_mode="HTML")

        elif text == "/note":
            sent = bot.sendMessage(chatId, "Carico...\nAspetta qualche secondo")
            response = api.note()
            updateDataDatabase(chatId, note=response)
            data = resp.parseNote(response)
            bot.editMessageText((chatId, sent['message_id']),
                                "❗️<b>Le tue note:</b>{0}".format(data), parse_mode="HTML")

        elif text == "/voti":
            sent = bot.sendMessage(chatId, "Carico...\nAspetta qualche secondo")
            response = api.voti()
            updateDataDatabase(chatId, voti=response)
            data = resp.parseVoti(response)
            bot.editMessageText((chatId, sent['message_id']),
                            "📝 <b>I tuoi voti</b>:\n{0}".format(data), parse_mode="HTML")

        elif text == "/assenze":
            sent = bot.sendMessage(chatId, "Carico...\nAspetta qualche secondo")
            response = api.assenze(inizioScuola.replace("/", ""))
            updateDataDatabase(chatId, assenze=response)
            data = resp.parseAssenze(response)
            bot.editMessageText((chatId, sent['message_id']), "{0}".format(data), parse_mode="HTML")

        elif text == "/agenda":
            sent = bot.sendMessage(chatId, "Carico...\nAspetta qualche secondo")
            response = api.agenda(14)
            updateDataDatabase(chatId, agenda=response)
            data = resp.parseAgenda(response)
            bot.editMessageText((chatId, sent['message_id']), "📆 <b>Agenda compiti delle prossime 2 settimane</b>:\n"
                                    "{0}".format(data), parse_mode="HTML")

        elif text == "/lezioni":
            sent = bot.sendMessage(chatId, "Carico...\nAspetta qualche secondo")
            data = resp.parseLezioni(api.lezioni())
            bot.editMessageText((chatId, sent['message_id']), "📚 <b>Lezioni di oggi</b>:\n\n"
                                              "{0}".format(data), parse_mode="HTML", reply_markup=None)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Prima", callback_data="lezioni_prima#{0}#0".format(sent['message_id'])),
                InlineKeyboardButton(text="Dopo ➡️", callback_data="lezioni_dopo#{0}#0".format(sent['message_id']))
            ]])
            bot.editMessageReplyMarkup((chatId, sent['message_id']), reply_markup=keyboard)

        elif text == "/aggiorna":
            sent = bot.sendMessage(chatId, "Carico...\nAspetta qualche secondo")
            try:
                userdata = data_db.search(where('id') == chatId)[0]

                newDidattica = api.didattica()
                newNote = api.note()
                newVoti = api.voti()
                newAssenze = api.assenze(inizioScuola.replace("/", ""))
                newAgenda = api.agenda(14)

                # oldDidattica = userdata['didattica']
                oldNote = userdata['note']
                oldVoti = userdata['voti']
                oldAssenze = userdata['assenze']
                oldAgenda = userdata['agenda']

                # dataDidattica = resp.parseNewDidattica(oldDidattica, newDidattica)
                dataNote = resp.parseNewNote(oldNote, newNote)
                dataVoti = resp.parseNewVoti(oldVoti, newVoti)
                dataAssenze = resp.parseNewAssenze(oldAssenze, newAssenze)
                dataAgenda = resp.parseNewAgenda(oldAgenda, newAgenda)

                firstMessage = True
                bot.deleteMessage((chatId, sent['message_id']))

                if dataNote is not None:
                    header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                    bot.editMessageText(chatId, header + "❗️<b>Nuove note</b>{0}\n\n\n".format(dataNote), parse_mode="HTML")
                    firstMessage = False

                if dataVoti is not None:
                    header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                    bot.sendMessage(chatId, header + "📝 <b>Nuovi voti</b>\n{0}\n\n\n".format(dataVoti), parse_mode="HTML")
                    firstMessage = False

                if dataAssenze is not None:
                    header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                    bot.sendMessage(chatId, header + "🏫 <b>Nuove assenze</b>{0}\n\n\n".format(dataAssenze), parse_mode="HTML")
                    firstMessage = False

                if dataAgenda is not None:
                    header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                    bot.sendMessage(chatId, header + "📆 <b>Nuovi impegni in agenda</b>\n{0}".format(dataAgenda), parse_mode="HTML")
                    firstMessage = False

                if firstMessage:
                    bot.sendMessage(chatId, "✅ Nessuna novità!")

                updateDataDatabase(chatId, newDidattica, newNote, newVoti, newAssenze, newAgenda)

            except IndexError:
                updateDataDatabase(chatId)
                bot.sendMessage(chatId, "😯 Errore!\nRiprova, per favore.")


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
    query_id, chatId, query_data = telepot.glance(msg, flavor="callback_query")
    query_split = query_data.split("#")
    message_id = int(query_split[1])
    button = query_split[0]

    try:
        api.login(db.search(where('id') == chatId)[0]['username'], decrypt(db.search(where('id') == chatId)[0]['password']))
    except AuthenticationFailedError:
        updateUserDatabase(chatId, username="", password="")
        bot.sendMessage(chatId, "😯 Le tue credenziali di accesso sono cambiate o sono errate.\n"
                                "Esegui nuovamente il /login per favore.")
        return 0

    if button == "lezioni_prima":
        selectedDay = int(query_split[2]) - 1
        dateformat = (datetime.now() + timedelta(days=selectedDay)).strftime("%d/%m/%Y")
        data = resp.parseLezioni(api.lezioni(selectedDay))
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Prima", callback_data="lezioni_prima#{0}#{1}".format(message_id, selectedDay)),
            InlineKeyboardButton(text="Dopo ➡️", callback_data="lezioni_dopo#{0}#{1}".format(message_id, selectedDay))
        ]])
        bot.editMessageText((chatId, message_id), "📚 <b>Lezioni del {0}</b>:\n\n"
                                                  "{1}".format(dateformat, data), parse_mode="HTML", reply_markup=keyboard)

    elif button == "lezioni_dopo":
        selectedDay = int(query_split[2]) + 1
        dateformat = (datetime.now() + timedelta(days=selectedDay)).strftime("%d/%m/%Y")
        data = resp.parseLezioni(api.lezioni(selectedDay))
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Prima", callback_data="lezioni_prima#{0}#{1}".format(message_id, selectedDay)),
            InlineKeyboardButton(text="Dopo ➡️", callback_data="lezioni_dopo#{0}#{1}".format(message_id, selectedDay))
        ]])
        bot.editMessageText((chatId, message_id), "📚 <b>Lezioni del {0}</b>:\n\n"
                                                  "{1}".format(dateformat, data), parse_mode="HTML", reply_markup=keyboard)

    api.logout()


def inline_query(msg):
    query_id, chatId, text = telepot.glance(msg, flavor='inline_query')

    if botStatus != "running":
        result = InlineQueryResultArticle(
            id=query_id,
            title="Errore",
            input_message_content=InputTextMessageContent(
                message_text="😴 Al momento sono impegnato, per favore riprova fra qualche minuto."
            )
        )
        options = [result]
        bot.answerInlineQuery(query_id, options, cache_time=10, is_personal=True, next_offset="")
        return 0

    try:
        api.login(db.search(where('id') == chatId)[0]['username'], decrypt(db.search(where('id') == chatId)[0]['password']))
    except AuthenticationFailedError:
        updateUserDatabase(chatId, username="", password="")
        result = InlineQueryResultArticle(
            id=query_id,
            title="Errore",
            input_message_content=InputTextMessageContent(
                message_text="Errore con le credenziali. Torna in chat per effettuare il login."
            )
        )
        options = [result]
        bot.answerInlineQuery(query_id, options, cache_time=10, is_personal=True, next_offset="")
        return 0


    if text == "didattica":
        data = resp.parseDidattica(api.didattica())
        result = InlineQueryResultArticle(
            id=query_id,
            title="Didattica",
            input_message_content=InputTextMessageContent(
                message_text="📚 <b>Files caricati in didadttica</b>:{0}".format(data),
                parse_mode="HTML"
            )
        )
        options = [result]

    elif text == "info":
        data = resp.parseInfo(api.info())
        result = InlineQueryResultArticle(
            id=query_id,
            title="Info",
            input_message_content=InputTextMessageContent(
                message_text="ℹ️ <b>Ecco le tue info</b>:\n\n{0}".format(data),
                parse_mode="HTML"
            )
        )
        options = [result]

    elif text == "prof":
        data = resp.parseMaterie(api.materie())
        result = InlineQueryResultArticle(
            id=query_id,
            title="Prof e materie",
            input_message_content=InputTextMessageContent(
                message_text="📚 <b>Lista materie e prof</b>:{0}".format(data),
                parse_mode="HTML"
            )
        )
        options = [result]

    elif text == "note":
        data = resp.parseNote(api.note())
        result = InlineQueryResultArticle(
            id=query_id,
            title="Note",
            input_message_content=InputTextMessageContent(
                message_text="❗️<b>Le tue note:</b>{0}".format(data),
                parse_mode="HTML"
            )
        )
        options = [result]

    elif text == "voti":
        data = resp.parseVoti(api.voti())
        result = InlineQueryResultArticle(
            id=query_id,
            title="Voti",
            input_message_content=InputTextMessageContent(
                message_text="📝 <b>I tuoi voti</b>:\n{0}".format(data),
                parse_mode="HTML"
            )
        )
        options = [result]

    elif text == "assenze":
        data = resp.parseAssenze(api.assenze(inizioScuola.replace("/", "")))
        result = InlineQueryResultArticle(
            id=query_id,
            title="Assenze",
            input_message_content=InputTextMessageContent(
                message_text="{0}".format(data),
                parse_mode="HTML"
            )
        )
        options = [result]

    elif text == "agenda":
        data = resp.parseAgenda(api.agenda(14))
        result = InlineQueryResultArticle(
            id=query_id,
            title="Agenda",
            input_message_content=InputTextMessageContent(
                message_text="📆 <b>Agenda compiti delle prossime 2 settimane</b>:\n"
                                                          "{0}".format(data),
                parse_mode="HTML"
            )
        )
        options = [result]

    else:
        result = InlineQueryResultArticle(
            id=query_id,
            title="Cosa vuoi sapere?",
            input_message_content=InputTextMessageContent(
                message_text="<i>Errore: nessun input specificato</i>",
                parse_mode="HTML"
            )
        )
        options = [result]

    bot.answerInlineQuery(query_id, options, cache_time=10, is_personal=True, next_offset="")
    api.logout()


bot.message_loop({'chat': reply, 'callback_query': button_press, 'inline_query': inline_query})
print("Bot started...")

while True:
    sleep(60)
    if datetime.now().hour in range(updatesStartHour, updatesStopHour):
        if datetime.now().minute == 0:
            botStatus = "notifying"
            runNotifications()
            botStatus = "running"
