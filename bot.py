﻿import telepot
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from telepot.exception import TelegramError, BotWasBlockedError
from time import sleep
from datetime import datetime, timedelta
from pony.orm import db_session, select, exists
from modules.session import ClasseVivaAPI, AuthenticationFailedError
import modules.responser as resp
from modules.crypter import crypt, decrypt
from modules.database import User, Data, ParsedData, db

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
supportApi = ClasseVivaAPI()
inizioScuola = "2018/09/10"
updatesStartHour = 7
updatesStopHour = 21
botStatus = "running"


@db_session
def isUserLogged(user):
    if (user.username != "") and (user.password != ""):
        return True
    else:
        return False


@db_session
def userLogin(user, use_support=False):
    try:
        if use_support:
            supportApi.login(user.username, decrypt(user.password))
        else:
            api.login(user.username, decrypt(user.password))
        return True
    except AuthenticationFailedError:
        clearUserData(user.chatId)
        try:
            bot.sendMessage(user.chatId, "😯 Le tue credenziali di accesso sono errate.\n"
                                         "Effettua nuovamente il /login per favore.")
        except (TelegramError, BotWasBlockedError):
            pass
        return False


def userLogout(use_support=False):
    if use_support:
        return supportApi.logout()
    else:
        return api.logout()


@db_session
def runUpdates():
    pendingUsers = select(user for user in User if user.password != "")[:]
    for currentUser in pendingUsers:

        if userLogin(currentUser, use_support=True):
            userdata = Data.get(chatId=currentUser.chatId)
            stored = ParsedData.get(chatId=currentUser.chatId)

            newDidattica = api.didattica()
            newInfo = api.info()
            newProf = api.materie()
            newNote = api.note()
            newVoti = api.voti()
            newAssenze = api.assenze(inizioScuola.replace("/", ""))
            newAgenda = api.agenda(14)
            newDomani = api.agenda(1)
            newLezioni = api.lezioni()

            userLogout(use_support=True)

            oldNote = userdata.note
            oldVoti = userdata.voti
            oldAssenze = userdata.assenze
            oldAgenda = userdata.agenda

            dataNote = resp.parseNewNote(oldNote, newNote)
            dataVoti = resp.parseNewVoti(oldVoti, newVoti)
            dataAssenze = resp.parseNewAssenze(oldAssenze, newAssenze)
            dataAgenda = resp.parseNewAgenda(oldAgenda, newAgenda)

            userdata.note = newNote
            userdata.voti = newVoti
            userdata.assenze = newAssenze
            userdata.agenda = newAgenda

            stored.didattica = resp.parseDidattica(newDidattica)
            stored.info = resp.parseInfo(newInfo)
            stored.prof = resp.parseMaterie(newProf)
            stored.note = resp.parseNote(newNote)
            stored.voti = resp.parseVoti(newVoti)
            stored.assenze = resp.parseAssenze(newAssenze)
            stored.agenda = resp.parseAgenda(newAgenda)
            stored.domani = resp.parseDomani(newDomani)
            stored.lezioni = resp.parseLezioni(newLezioni)

            try:
                firstMessage = True

                if dataNote is not None:
                    header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                    bot.sendMessage(currentUser.chatId, header + "❗️<b>Nuove note</b>{0}\n\n\n".format(dataNote), parse_mode="HTML")
                    firstMessage = False

                if dataVoti is not None:
                    header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                    bot.sendMessage(currentUser.chatId, header + "📝 <b>Nuovi voti</b>\n{0}\n\n\n".format(dataVoti), parse_mode="HTML")
                    firstMessage = False

                if dataAssenze is not None:
                    header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                    bot.sendMessage(currentUser.chatId, header + "🏫 <b>Nuove assenze</b>{0}\n\n\n".format(dataAssenze), parse_mode="HTML")
                    firstMessage = False

                if dataAgenda is not None:
                    header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                    bot.sendMessage(currentUser.chatId, header + "📆 <b>Nuovi impegni in agenda</b>\n{0}".format(dataAgenda), parse_mode="HTML")

            except (TelegramError, BotWasBlockedError):
                pass


@db_session
def clearUserData(chatId):
    user = User.get(chatId=chatId)
    userdata = Data.get(chatId=chatId)
    parseddata = ParsedData.get(chatId=chatId)

    user.username = ""
    user.password = ""
    user.status = "normal"
    userdata.didattica = {}
    userdata.info = {}
    userdata.prof = {}
    userdata.note = {}
    userdata.voti = {}
    userdata.assenze = {}
    userdata.agenda = {}
    userdata.domani = {}
    userdata.lezioni = {}
    parseddata.didattica = ""
    parseddata.info = ""
    parseddata.prof = ""
    parseddata.note = ""
    parseddata.voti = ""
    parseddata.assenze = ""
    parseddata.agenda = ""
    parseddata.domani = ""
    parseddata.lezioni = ""



@db_session
def reply(msg):
    msgType, chatType, chatId = telepot.glance(msg)
    text = msg['text']
    name = msg['from']['first_name']

    if not User.exists(lambda u: u.chatId == chatId):
        User(chatId=chatId)

    if not Data.exists(lambda u: u.chatId == chatId):
        Data(chatId=chatId)

    if not ParsedData.exists(lambda u: u.chatId == chatId):
        ParsedData(chatId=chatId)

    user = User.get(chatId=chatId)
    userdata = Data.get(chatId=chatId)
    stored = ParsedData.get(chatId=chatId)

    if botStatus != "running":
        bot.sendMessage(chatId, "😴 Al momento sono impegnato, per favore riprova fra qualche minuto.")
        return 0

    if user.status != "normal":
        if text == "/annulla":
            user.status = "normal"
            bot.sendMessage(chatId, "Comando annullato!")

        elif user.status == "login_0":
            user.username = text
            user.status = "login_1"
            bot.sendMessage(chatId, "👍 Ottimo. Adesso inviami la password.\n"
                                    "Ricorda che la password viene salvata solo per te e viene criptata, nessuno potrà leggerla.")

        elif user.status == "login_1":
            user.password = crypt(text)
            user.status = "normal"

            if userLogin(user):
                bot.sendMessage(chatId, "Fatto 😊\n"
                                        "Premi /help per vedere la lista dei comandi disponibili.")
                userLogout()


    elif text == "/help":
        message = "Ciao, sono il bot di <b>ClasseViva</b>!\n" \
                  "Posso aiutarti a <b>navigare</b> nel registro e posso mandarti <b>notifiche</b> quando hai nuovi avvisi.\n\n" \
                  "<b>Lista dei comandi</b>:\n\n" \
                  "/start - Avvia il bot\n\n" \
                  "/help - Visualizza questo messaggio\n\n" \
                  "/login - Effettua il login\n\n" \
                  "/logout - Disconnettiti\n\n" \
                  "/aggiorna - Aggiorna manualmente tutti i dati, per controllare se ci sono nuovi avvisi.\n" \
                                "Oppure, puoi lasciarlo fare a me, ogni mezz'ora :)\n\n" \
                  "/agenda - Visualizza agenda (compiti e verifiche)\n\n" \
                  "/domani - Vedi i compiti che hai per domani\n\n" \
                  "/assenze - Visualizza assenze, ritardi e uscite anticipate\n\n" \
                  "/didattica - Visualizza la lista dei file in didattica\n\n" \
                  "/lezioni - Visualizza la lista delle lezioni\n\n" \
                  "/voti - Visualizza la lista dei voti\n\n" \
                  "/note - Visualizza la lista delle note\n\n" \
                  "/info - Visualizza le tue info utente\n\n" \
                  "/prof - Visualizza la lista delle materie e dei prof\n\n" \
                  "\n" \
                  "<b>Notifiche</b>: ogni mezz'ora, ti invierò un messagio se ti sono arrivati nuovi voti, note, compiti o assenze."
        bot.sendMessage(chatId, message, parse_mode="HTML")

    elif isUserLogged(user):

        if text == "/start":
            bot.sendMessage(chatId, "Bentornato, <b>{0}</b>!\n"
                                    "Cosa posso fare per te? 😊".format(name), parse_mode="HTML")

        elif text == "/login":
            bot.sendMessage(chatId, "Sei già loggato.\n"
                                    "Premi /logout per uscire.")

        elif text == "/logout":
            clearUserData(chatId)
            bot.sendMessage(chatId, "😯 Fatto, sei stato disconnesso!\n"
                                    "Premi /login per entrare di nuovo.\n\n"
                                    "Premi /help se serve aiuto.")

        elif text == "/didattica":
            bot.sendMessage(chatId, "📚 <b>Files caricati in didadttica</b>:{0}".format(stored.didattica), parse_mode="HTML")

        elif text == "/info":
            bot.sendMessage(chatId, "ℹ️ <b>Ecco le tue info</b>:\n\n"
                                    "{0}".format(stored.info), parse_mode="HTML")

        elif text == "/prof":
            bot.sendMessage(chatId, "📚 <b>Lista materie e prof</b>:{0}".format(stored.prof), parse_mode="HTML")

        elif text == "/note":
            bot.sendMessage(chatId, "❗️<b>Le tue note:</b>{0}".format(stored.note), parse_mode="HTML")

        elif text == "/voti":
            bot.sendMessage(chatId, "📝 <b>I tuoi voti</b>:\n"
                                    "{0}".format(stored.voti), parse_mode="HTML")

        elif text == "/assenze":
            bot.sendMessage(chatId, "{0}".format(stored.assenze), parse_mode="HTML")

        elif text == "/agenda":
            bot.sendMessage(chatId, "📆 <b>Agenda compiti delle prossime 2 settimane</b>:\n"
                                    "{0}".format(stored.agenda), parse_mode="HTML")

        elif text == "/domani":
            bot.sendMessage(chatId, "📆 <b>Compiti e verifiche per domani</b>:\n"
                                    "{0}".format(stored.domani), parse_mode="HTML")

        elif text == "/lezioni":
            sent = bot.sendMessage(chatId, "📚 <b>Lezioni di oggi</b>:\n\n"
                                    "{0}".format(stored.lezioni), parse_mode="HTML", reply_markup=None)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Prima", callback_data="lezioni_prima#{0}#0".format(sent['message_id'])),
                InlineKeyboardButton(text="Dopo ➡️", callback_data="lezioni_dopo#{0}#0".format(sent['message_id']))
            ]])
            bot.editMessageReplyMarkup((chatId, sent['message_id']), keyboard)

        elif text == "/aggiorna":
            sent = bot.sendMessage(chatId, "🔍 Cerco aggiornamenti...")

            if userLogin(user):

                newDidattica = api.didattica()
                newInfo = api.info()
                newProf = api.materie()
                newNote = api.note()
                newVoti = api.voti()
                newAssenze = api.assenze(inizioScuola.replace("/", ""))
                newAgenda = api.agenda(14)
                newDomani = api.agenda(1)
                newLezioni = api.lezioni()

                userLogout()

                oldNote = userdata.note
                oldVoti = userdata.voti
                oldAssenze = userdata.assenze
                oldAgenda = userdata.agenda

                dataNote = resp.parseNewNote(oldNote, newNote)
                dataVoti = resp.parseNewVoti(oldVoti, newVoti)
                dataAssenze = resp.parseNewAssenze(oldAssenze, newAssenze)
                dataAgenda = resp.parseNewAgenda(oldAgenda, newAgenda)

                userdata.note = newNote
                userdata.voti = newVoti
                userdata.assenze = newAssenze
                userdata.agenda = newAgenda

                stored.didattica = resp.parseDidattica(newDidattica)
                stored.info = resp.parseInfo(newInfo)
                stored.prof = resp.parseMaterie(newProf)
                stored.note = resp.parseNote(newNote)
                stored.voti = resp.parseVoti(newVoti)
                stored.assenze = resp.parseAssenze(newAssenze)
                stored.agenda = resp.parseAgenda(newAgenda)
                stored.domani = resp.parseDomani(newDomani)
                stored.lezioni = resp.parseLezioni(newLezioni)

                firstMessage = True
                bot.deleteMessage((chatId, sent['message_id']))

                if dataNote is not None:
                    header = "🔔 <b>Hai nuove notifiche!</b>\n\n" if firstMessage else ""
                    bot.sendMessage(chatId, header + "❗️<b>Nuove note</b>{0}\n\n\n".format(dataNote), parse_mode="HTML")
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

                if firstMessage:
                    bot.sendMessage(chatId, "✅ Dati aggiornati!\n"
                                            "✅ Nessuna novità!")


        else:
            bot.sendMessage(chatId, "Non ho capito...\n"
                                    "Serve aiuto? Premi /help")


    else:
        if text == "/login":
            user.status = "login_0"
            bot.sendMessage(chatId, "Per favore, inviami il tuo <b>username</b> (quello che usi per accedere al registro).\n"
                                    "Usa /annulla se serve.", parse_mode="HTML")

        else:
            bot.sendMessage(chatId, "Benvenuto, <b>{0}</b>!\n"
                                    "Per favore, premi /login per utilizzarmi.\n\n"
                                    "Premi /help se serve aiuto.".format(name), parse_mode="HTML")


@db_session
def button_press(msg):
    query_id, chatId, query_data = telepot.glance(msg, flavor="callback_query")
    user = User.get(chatId=chatId)
    query_split = query_data.split("#")
    message_id = int(query_split[1])
    button = query_split[0]

    if userLogin(user):

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

        userLogout()


bot.message_loop({'chat': reply, 'callback_query': button_press})
print("Bot started...")

while True:
    sleep(60)
    if datetime.now().hour in range(updatesStartHour, updatesStopHour):
        if datetime.now().minute in [0, 30]:
            runUpdates()