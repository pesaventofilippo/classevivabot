import telepot
from telepot.exception import TelegramError, BotWasBlockedError
from time import sleep
from datetime import datetime, timedelta
from pony.orm import db_session, select
from modules.session import ClasseVivaAPI, AuthenticationFailedError, ApiServerError
import modules.responser as resp
from modules.helpers import sendLongMessage
import modules.keyboards as keyboards
from modules.crypter import crypt, decrypt
from modules.database import User, Data, ParsedData, Settings

try:
    f = open('token.txt', 'r')
    token = f.readline().strip()
    f.close()
except FileNotFoundError:
    token = input("Please paste the bot Token here: ")
    f = open('token.txt', 'w')
    f.write(token)
    f.close()

bot = telepot.Bot(token)
api = ClasseVivaAPI()
supportApi = ClasseVivaAPI()
adminIds = [368894926] # Bot Creator


@db_session
def isUserLogged(user):
    return (user.username != "") and (user.password != "")


@db_session
def clearUserData(user):
    user.username = ""
    user.password = ""
    user.status = "normal"
    user.lastPeriod = 1

    userdata = Data.get(chatId=user.chatId)
    userdata.didattica = {}
    userdata.info = {}
    userdata.prof = {}
    userdata.note = {}
    userdata.voti = {}
    userdata.assenze = {}
    userdata.agenda = {}
    userdata.domani = {}
    userdata.lezioni = {}

    stored = ParsedData.get(chatId=user.chatId)
    stored.didattica = ""
    stored.info = ""
    stored.prof = ""
    stored.note = ""
    stored.voti = ""
    stored.assenze = ""
    stored.agenda = ""
    stored.domani = ""
    stored.lezioni = ""


@db_session
def userLogin(user, api_type=api):
    if not isUserLogged(user):
        return False
    try:
        api_type.login(user.username, decrypt(user.password))
        return True
    except AuthenticationFailedError:
        clearUserData(user)
        try:
            bot.sendMessage(user.chatId, "😯 Le tue credenziali di accesso sono errate.\n"
                                         "Effettua nuovamente il /login per favore.")
        except (TelegramError, BotWasBlockedError):
            pass
        return False
    except ApiServerError:
        try:
            bot.sendMessage(user.chatId, "⚠️ I server di ClasseViva non sono raggiungibili.\n"
                                         "Riprova tra qualche minuto.")
        except (TelegramError, BotWasBlockedError):
            pass
        return False


def userLogout(api_type=api):
    api_type.logout()


@db_session
def fetchAndStore(user, api_type):
    newDidattica = api_type.didattica()
    newInfo = api_type.info()
    newProf = api_type.materie()
    newNote = api_type.note()
    newVoti = api_type.voti()
    newAssenze = api_type.assenze()
    newAgenda = api_type.agenda(14)
    newLezioni = api_type.lezioni()
    userLogout(api_type)

    stored = ParsedData.get(chatId=user.chatId)
    stored.didattica = resp.parseDidattica(newDidattica)
    stored.info = resp.parseInfo(newInfo)
    stored.prof = resp.parseMaterie(newProf)
    stored.note = resp.parseNote(newNote)
    stored.voti = resp.parseVoti(newVoti, user)
    stored.assenze = resp.parseAssenze(newAssenze)
    stored.agenda = resp.parseAgenda(newAgenda)
    stored.domani = resp.parseDomani(newAgenda)
    stored.lezioni = resp.parseLezioni(newLezioni)

    return newDidattica, newNote, newVoti, newAgenda


@db_session
def updateUserdata(user, newDidattica, newNote, newVoti, newAgenda):
    userdata = Data.get(chatId=user.chatId)
    userdata.didattica = newDidattica
    userdata.note = newNote
    userdata.voti = newVoti
    userdata.agenda = newAgenda


@db_session
def runUpdates():
    crhour = datetime.now().hour
    pendingUsers = select(user for user in User if user.password != "")[:]

    for currentUser in pendingUsers:

        if userLogin(currentUser, supportApi):
            userdata = Data.get(chatId=currentUser.chatId)
            settings = Settings.get(chatId=currentUser.chatId)
            try:
                newDidattica, newNote, newVoti, newAgenda = fetchAndStore(currentUser, supportApi)
            except ApiServerError:
                break

            if settings.wantsNotifications is True:
                if (settings.doNotDisturb is False) or (crhour in range(7, 21)):
                    dataDidattica = resp.parseNewDidattica(userdata.didattica, newDidattica)
                    dataNote = resp.parseNewNote(userdata.note, newNote)
                    dataVoti = resp.parseNewVoti(userdata.voti, newVoti, currentUser)
                    dataAgenda = resp.parseNewAgenda(userdata.agenda, newAgenda)
                    updateUserdata(currentUser, newDidattica, newNote, newVoti, newAgenda)
                    try:
                        if dataDidattica and "didattica" in settings.activeNews:
                            bot.sendMessage(currentUser.chatId, "🔔 <b>Nuovi file caricati!</b>"
                                                                "{0}".format(dataDidattica), parse_mode="HTML")
                        if dataNote and "note" in settings.activeNews:
                            bot.sendMessage(currentUser.chatId, "🔔 <b>Hai nuove note!</b>"
                                                                "{0}".format(dataNote), parse_mode="HTML")
                        if dataVoti and "voti" in settings.activeNews:
                            bot.sendMessage(currentUser.chatId, "🔔 <b>Hai nuovi voti!</b>"
                                                                "{0}".format(dataVoti), parse_mode="HTML")
                        if dataAgenda and "agenda" in settings.activeNews:
                            bot.sendMessage(currentUser.chatId, "🔔 <b>Hai nuovi impegni!</b>\n"
                                                                "{0}".format(dataAgenda), parse_mode="HTML")
                    except BotWasBlockedError:
                        clearUserData(currentUser)
                    except TelegramError:
                        pass


@db_session
def runDailyUpdates(crminute):
    crhour = datetime.now().hour
    pendingUsers = select(user for user in User if user.password != "")[:]
    for currentUser in pendingUsers:
        settings = Settings.get(chatId=currentUser.chatId)
        if settings.wantsDailyUpdates:
            hoursplit = settings.dailyUpdatesHour.split(":")
            if (int(hoursplit[0]) == crhour) and (int(hoursplit[1]) == crminute):
                stored = ParsedData.get(chatId=currentUser.chatId)
                try:
                    bot.sendMessage(currentUser.chatId, "🕙 <b>Promemoria!</b>\n\n"
                                                        "📆 <b>Cosa devi fare per domani</b>:\n\n"
                                                        "{0}\n\n\n"
                                                        "📚 <b>Le lezioni di oggi</b>:\n\n"
                                                        "{1}".format(stored.domani, stored.lezioni), parse_mode="HTML")
                except BotWasBlockedError:
                    clearUserData(currentUser)
                except TelegramError:
                    pass


@db_session
def reply(msg):
    chatId = msg['chat']['id']
    text = msg['text']
    name = msg['from']['first_name']

    if not User.exists(lambda u: u.chatId == chatId):
        User(chatId=chatId)

    if not Data.exists(lambda u: u.chatId == chatId):
        Data(chatId=chatId)

    if not ParsedData.exists(lambda u: u.chatId == chatId):
        ParsedData(chatId=chatId)

    if not Settings.exists(lambda u: u.chatId == chatId):
        Settings(chatId=chatId)

    user = User.get(chatId=chatId)
    userdata = Data.get(chatId=chatId)
    stored = ParsedData.get(chatId=chatId)

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
                sent = bot.sendMessage(chatId, "🔍 Aggiorno il profilo...")
                newDidattica, newNote, newVoti, newAgenda = fetchAndStore(user, api)
                updateUserdata(user, newDidattica, newNote, newVoti, newAgenda)
                bot.editMessageText((chatId, sent['message_id']), "✅ Profilo aggiornato!")

        elif user.status == "calling_support":
            user.status = "normal"
            for a in adminIds:
                bot.sendMessage(a, "🆘 <b>Richiesta di aiuto</b>\n"
                                   "Da: <a href=\"tg://user?id={0}\">{1}</a>\n"
                                   "<i>Rispondi al messaggio per parlare con l'utente.</i>".format(chatId, name), parse_mode="HTML")
                bot.forwardMessage(a, chatId, msg['message_id'])
            bot.sendMessage(chatId, "<i>Richiesta inviata.</i>\n"
                                    "Un admin ti risponderà il prima possibile.", parse_mode="HTML")


    elif text == "/help":
        message = "Ciao, sono il bot di <b>ClasseViva</b>! 👋🏻\n" \
                  "Posso aiutarti a <b>navigare</b> nel registro e posso mandarti <b>notifiche</b> quando hai nuovi avvisi.\n\n" \
                  "<b>Lista dei comandi</b>:\n" \
                  "- /login - Effettua il login\n" \
                  "- /logout - Disconnettiti\n" \
                  "- /aggiorna - Aggiorna manualmente tutti i dati, per controllare se ci sono nuovi avvisi.\n" \
                               "Oppure, puoi lasciarlo fare a me, ogni mezz'ora :)\n" \
                  "- /promemoria - Vedi un promemoria con i compiti da fare per domani e le lezioni svolte oggi.\n" \
                  "- /agenda - Visualizza agenda (compiti e verifiche)\n" \
                  "- /domani - Vedi i compiti che hai per domani\n" \
                  "- /assenze - Visualizza assenze, ritardi e uscite anticipate\n" \
                  "- /didattica - Visualizza la lista dei file in didattica\n" \
                  "- /lezioni - Visualizza la lista delle lezioni\n" \
                  "- /voti - Visualizza la lista dei voti\n" \
                  "- /note - Visualizza la lista delle note\n" \
                  "- /info - Visualizza le tue info utente\n" \
                  "- /prof - Visualizza la lista delle materie e dei prof\n" \
                  "- /settings - Modifica le impostazioni personali del bot\n" \
                  "- /dona - Supporta il bot e il mio lavoro, se ti senti generoso :)\n" \
                  "- /about - Informazioni sul bot\n" \
                  "- /support - Contatta lo staff (emergenze)\n\n" \
                  "<b>Notifiche</b>: ogni mezz'ora, se vuoi, ti invierò un messaggio se ti sono arrivati nuovi voti, note, compiti o materiali."
        bot.sendMessage(chatId, message, parse_mode="HTML")

    elif text == "/dona":
        bot.sendMessage(chatId, "<b>Grazie per aver pensato di supportarmi!</b>\n"
                                "Ho dedicato ore di lavoro a questo bot, ma ho deciso di renderlo open-source e completamente gratuito.\n"
                                "Tuttavia, il numero di utenti che usano questo bot continua a crescere, e crescono anche i costi di gestione del server. "
                                "Non preoccuparti, per adesso non è un problema e questo bot continuerà ad essere gratuito, ma se proprio ti senti generoso e "
                                "hai voglia di farmi un regalo, sei il benvenuto :)\n\n"
                                "<i>Grazie di cuore.</i> ❤️", parse_mode="HTML", reply_markup=keyboards.payments())

    elif text == "/about":
        bot.sendMessage(chatId, "ℹ️ <b>Informazioni sul bot</b>\n"
                                "ClasseVivaBot è un bot creato e sviluppato da Filippo Pesavento, che ti può aiutare "
                                "durante l'anno scolastico mandando notifiche per le novità del registro e molto altro.\n"
                                "Prova ad usarlo per scoprire quanto è comodo!\n\n"
                                "<b>Sviluppo:</b> Filippo Pesavento\n"
                                "<b>Hosting:</b> Filippo Pesavento\n"
                                "<a href=\"https://pesaventofilippo.tk/projects/classevivabot\">Altre info & Privacy Policy</a>", parse_mode="HTML")

    elif text.startswith("/broadcast "):
        if chatId in adminIds:
            bdText = text.split(" ", 1)[1]
            pendingUsers = select(user for user in User if user.password != "")[:]
            for user in pendingUsers:
                try:
                    bot.sendMessage(user.chatId, bdText, parse_mode="HTML", disable_web_page_preview=True)
                except (TelegramError, BotWasBlockedError):
                    pass
            bot.sendMessage(chatId, "📢 Messaggio inviato correttamente a {0} utenti!".format(pendingUsers.__len__()))

    elif text.startswith("/sendmsg "):
        if chatId in adminIds:
            selId = int(text.split(" ", 2)[1])
            selText = str(text.split(" ", 2)[2])
            bot.sendMessage(selId, selText, parse_mode="HTML")
            bot.sendMessage(chatId, selText + "\n\n- Messaggio inviato!", parse_mode="HTML")

    elif "reply_to_message" in msg:
        if chatId in adminIds:
            userId = msg['reply_to_message']['forward_from']['id']
            bot.sendMessage(userId, "💬 <b>Risposta dello staff</b>\n"
                                    "{0}".format(text), parse_mode="HTML")
            bot.sendMessage(chatId, "Risposta inviata!")
        else:
            bot.sendMessage(chatId, "Premi /support per parlare con lo staff.")

    elif isUserLogged(user):
        if text == "/start":
            bot.sendMessage(chatId, "Bentornato, <b>{0}</b>!\n"
                                    "Cosa posso fare per te? 😊".format(name), parse_mode="HTML")

        elif text == "/login":
            bot.sendMessage(chatId, "Sei già loggato.\n"
                                    "Premi /logout per uscire.")

        elif text == "/logout":
            sent = bot.sendMessage(chatId, "Tutti i tuoi dati scolastici e le credenziali verranno eliminate dal bot.\n"
                                           "Sei <b>veramente sicuro</b> di voler uscire?", parse_mode="HTML")
            bot.editMessageReplyMarkup((chatId, sent['message_id']), keyboards.logout(sent['message_id']))

        elif text == "/didattica":
            sendLongMessage(bot, chatId, "📚 <b>Files caricati in didadttica</b>:\n\n"
                                         "{0}".format(stored.didattica), parse_mode="HTML")

        elif text == "/info":
            bot.sendMessage(chatId, "ℹ️ <b>Ecco le tue info</b>:\n\n"
                                    "{0}".format(stored.info), parse_mode="HTML")

        elif text == "/prof":
            sendLongMessage(bot, chatId, "📚 <b>Lista materie e prof</b>:\n\n"
                                         "{0}".format(stored.prof), parse_mode="HTML")

        elif text == "/note":
            sendLongMessage(bot, chatId, "❗️<b>Le tue note</b>:\n\n"
                                         "{0}".format(stored.note), parse_mode="HTML")

        elif text == "/voti":
            sendLongMessage(bot, chatId, "📝 <b>I tuoi voti</b>:\n\n"
                                         "{0}".format(stored.voti), parse_mode="HTML")

        elif text == "/assenze":
            sendLongMessage(bot, chatId, "{0}".format(stored.assenze), parse_mode="HTML")

        elif text == "/agenda":
            bot.sendMessage(chatId, "📆 <b>Agenda compiti delle prossime 2 settimane</b>:\n\n"
                                    "{0}".format(stored.agenda), parse_mode="HTML")

        elif text == "/domani":
            bot.sendMessage(chatId, "📆 <b>Compiti e verifiche per domani</b>:\n\n"
                                    "{0}".format(stored.domani), parse_mode="HTML")

        elif text == "/lezioni":
            sent = bot.sendMessage(chatId, "📚 <b>Lezioni di oggi</b>:\n\n"
                                           "{0}".format(stored.lezioni), parse_mode="HTML", reply_markup=None)
            bot.editMessageReplyMarkup((chatId, sent['message_id']), keyboards.lezioni(sent['message_id']))

        elif text == "/settings":
            sent = bot.sendMessage(chatId, "🛠 <b>Impostazioni</b>\n"
                                           "Ecco le impostazioni del bot. Cosa vuoi modificare?", parse_mode="HTML", reply_markup=None)
            bot.editMessageReplyMarkup((chatId, sent['message_id']), keyboards.settings_menu(sent['message_id']))

        elif text == "/promemoria":
            bot.sendMessage(chatId, "🕙 <b>Promemoria!</b>\n\n"
                                    "📆 <b>Cosa devi fare per domani</b>:\n\n"
                                    "{0}\n\n\n"
                                    "📚 <b>Le lezioni di oggi</b>:\n\n"
                                    "{1}".format(stored.domani, stored.lezioni), parse_mode="HTML")

        elif text == "/aggiorna":
            sent = bot.sendMessage(chatId, "🔍 Cerco aggiornamenti...")
            if userLogin(user):
                try:
                    newDidattica, newNote, newVoti, newAgenda = fetchAndStore(user, api)
                except ApiServerError:
                    bot.sendMessage(chatId, "⚠️ I server di ClasseViva non sono raggiungibili.\n"
                                            "Riprova tra qualche minuto.")
                    return
                dataDidattica = resp.parseNewDidattica(userdata.didattica, newDidattica)
                dataNote = resp.parseNewNote(userdata.note, newNote)
                dataVoti = resp.parseNewVoti(userdata.voti, newVoti, user)
                dataAgenda = resp.parseNewAgenda(userdata.agenda, newAgenda)
                updateUserdata(user, newDidattica, newNote, newVoti, newAgenda)

                if dataDidattica is not None:
                    bot.sendMessage(chatId, "🔔 <b>Nuovi file caricati!</b>{0}".format(dataDidattica), parse_mode="HTML")

                if dataNote is not None:
                    bot.sendMessage(chatId, "🔔 <b>Hai nuove note!</b>{0}".format(dataNote), parse_mode="HTML")

                if dataVoti is not None:
                    bot.sendMessage(chatId, "🔔 <b>Hai nuovi voti!</b>{0}".format(dataVoti), parse_mode="HTML")

                if dataAgenda is not None:
                    bot.sendMessage(chatId, "🔔 <b>Hai nuovi impegni!</b>\n{0}".format(dataAgenda), parse_mode="HTML")

                if not any([dataDidattica, dataNote, dataVoti, dataAgenda]):
                    bot.editMessageText((chatId, sent['message_id']), "✅ Dati aggiornati!\n"
                                                                      "✅ Nessuna novità!")

        elif text == "/support":
            user.status = "calling_support"
            bot.sendMessage(chatId, "🆘 <b>Richiesta di supporto</b>\n"
                                    "Se hai qualche problema che non riesci a risolvere, scrivi qui un messaggio, e un admin "
                                    "ti contatterà entro 24 ore.\n\n"
                                    "<i>Per annullare, premi</i> /annulla.", parse_mode="HTML")

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
    chatId, query_data = telepot.glance(msg, flavor="callback_query")[1:3]
    user = User.get(chatId=chatId)
    settings = Settings.get(chatId=chatId)
    query_split = query_data.split("#")
    message_id = int(query_split[1])
    button = query_split[0]

    if button == "settings_main":
        bot.editMessageText((chatId, message_id), "🛠 <b>Impostazioni</b>\n"
                                                    "Ecco le impostazioni del bot. Cosa vuoi modificare?",
                                                     parse_mode="HTML", reply_markup=keyboards.settings_menu(message_id))

    elif button == "settings_notifications":
        bot.editMessageText((chatId, message_id), "<b>Preferenze notifiche</b>\n"
                                                  "- Stato attuale: {0}\n\n"
                                                  "Vuoi che ti mandi notifiche se trovo novità?\n"
                                                  "<b>Nota</b>: Se non vuoi riceverle di notte, puoi impostarlo a parte."
                                                  "".format("🔔 Attivo" if settings.wantsNotifications else "🔕 Disattivo"),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_notifications(message_id))

    elif button == "settings_donotdisturb":
        bot.editMessageText((chatId, message_id), "<b>Preferenze modalità notturna</b>\n"
                                                  "- Stato attuale: {0}\n\n"
                                                  "Vuoi che silenzi le notifiche nella fascia oraria notturna (21:00 - 7:00)?"
                                                  "".format("😴 Attivo" if settings.doNotDisturb else "🔔 Suona"),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_donotdisturb(message_id))

    elif button == "settings_dailynotif":
        bot.editMessageText((chatId, message_id), "<b>Preferenze notifiche giornaliere</b>\n"
                                                  "- Stato attuale: {0}\n"
                                                  "- Orario notifiche: {1}\n\n"
                                                  "Vuoi che ti dica ogni giorno i compiti per il giorno successivo e le lezioni svolte?"
                                                  "".format("🔔 Attiva" if settings.wantsDailyUpdates else "🔕 Disattiva", settings.dailyUpdatesHour),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_dailynotif(message_id))

    elif button == "settings_selectnews":
        bot.editMessageText((chatId, message_id), "📲 <b>Selezione notifiche</b>\n\n"
                                                  "📚 Didattica: {0}\n"
                                                  "❗️ Note: {1}\n"
                                                  "📝 Voti: {2}\n"
                                                  "📆 Agenda: {3}\n\n"
                                                  "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                  "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo"),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_selectnews(message_id))

    elif button == "news_didattica":
        if "didattica" in settings.activeNews:
            settings.activeNews.remove("didattica")
        else:
            settings.activeNews.append("didattica")
        bot.editMessageText((chatId, message_id), "📲 <b>Selezione notifiche</b>\n\n"
                                                      "📚 Didattica: {0}\n"
                                                      "❗️ Note: {1}\n"
                                                      "📝 Voti: {2}\n"
                                                      "📆 Agenda: {3}\n\n"
                                                      "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                      "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo"),
                                                        parse_mode="HTML", reply_markup=keyboards.settings_selectnews(message_id))

    elif button == "news_note":
        if "note" in settings.activeNews:
            settings.activeNews.remove("note")
        else:
            settings.activeNews.append("note")
        bot.editMessageText((chatId, message_id), "📲 <b>Selezione notifiche</b>\n\n"
                                                      "📚 Didattica: {0}\n"
                                                      "❗️ Note: {1}\n"
                                                      "📝 Voti: {2}\n"
                                                      "📆 Agenda: {3}\n\n"
                                                      "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                      "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo"),
                                                        parse_mode="HTML", reply_markup=keyboards.settings_selectnews(message_id))

    elif button == "news_voti":
        if "voti" in settings.activeNews:
            settings.activeNews.remove("voti")
        else:
            settings.activeNews.append("voti")
        bot.editMessageText((chatId, message_id), "📲 <b>Selezione notifiche</b>\n\n"
                                                      "📚 Didattica: {0}\n"
                                                      "❗️ Note: {1}\n"
                                                      "📝 Voti: {2}\n"
                                                      "📆 Agenda: {3}\n\n"
                                                      "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                      "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo"),
                                                        parse_mode="HTML", reply_markup=keyboards.settings_selectnews(message_id))

    elif button == "news_agenda":
        if "agenda" in settings.activeNews:
            settings.activeNews.remove("agenda")
        else:
            settings.activeNews.append("agenda")
        bot.editMessageText((chatId, message_id), "📲 <b>Selezione notifiche</b>\n\n"
                                                      "📚 Didattica: {0}\n"
                                                      "❗️ Note: {1}\n"
                                                      "📝 Voti: {2}\n"
                                                      "📆 Agenda: {3}\n\n"
                                                      "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                      "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                                "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo"),
                                                        parse_mode="HTML", reply_markup=keyboards.settings_selectnews(message_id))

    elif button == "settings_notif_yes":
        settings.wantsNotifications = True
        bot.editMessageText((chatId, message_id), "<b>Preferenze notifiche</b>\n"
                                                  "- Stato attuale: {0}\n\n"
                                                  "Vuoi che ti mandi notifiche se trovo novità?\n"
                                                  "<b>Nota</b>: Se non vuoi riceverle di notte, puoi impostarlo a parte."
                                                  "".format("🔔 Attivo" if settings.wantsNotifications else "🔕 Disattivo"),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_notifications(message_id))

    elif button == "settings_notif_no":
        settings.wantsNotifications = False
        bot.editMessageText((chatId, message_id), "<b>Preferenze notifiche</b>\n"
                                                  "- Stato attuale: {0}\n\n"
                                                  "Vuoi che ti mandi notifiche se trovo novità?\n"
                                                  "<b>Nota</b>: Se non vuoi riceverle di notte, puoi impostarlo a parte."
                                                  "".format("🔔 Attivo" if settings.wantsNotifications else "🔕 Disattivo"),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_notifications(message_id))

    elif button == "settings_night_yes":
        settings.doNotDisturb = True
        bot.editMessageText((chatId, message_id), "<b>Preferenze modalità notturna</b>\n"
                                                  "- Stato attuale: {0}\n\n"
                                                  "Vuoi che silenzi le notifiche nella fascia oraria notturna (21:00 - 7:00)?"
                                                  "".format("😴 Attivo" if settings.doNotDisturb else "🔔 Suona"),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_donotdisturb(message_id))

    elif button == "settings_night_no":
        settings.doNotDisturb = False
        bot.editMessageText((chatId, message_id), "<b>Preferenze modalità notturna</b>\n"
                                                  "- Stato attuale: {0}\n\n"
                                                  "Vuoi che silenzi le notifiche nella fascia oraria notturna (21:00 - 7:00)?"
                                                  "".format("😴 Attivo" if settings.doNotDisturb else "🔔 Suona"),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_donotdisturb(message_id))

    elif button == "settings_daily_yes":
        settings.wantsDailyUpdates = True
        bot.editMessageText((chatId, message_id), "<b>Preferenze notifiche giornaliere</b>\n"
                                                  "- Stato attuale: {0}\n"
                                                  "- Orario notifiche: {1}\n\n"
                                                  "Vuoi che ti dica ogni giorno i compiti per il giorno successivo e le lezioni svolte?"
                                                  "".format("🔔 Attiva" if settings.wantsDailyUpdates else "🔕 Disattiva", settings.dailyUpdatesHour),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_dailynotif(message_id))

    elif button == "settings_daily_no":
        settings.wantsDailyUpdates = False
        bot.editMessageText((chatId, message_id), "<b>Preferenze notifiche giornaliere</b>\n"
                                                  "- Stato attuale: {0}\n"
                                                  "- Orario notifiche: {1}\n\n"
                                                  "Vuoi che ti dica ogni giorno i compiti per il giorno successivo e le lezioni svolte?"
                                                  "".format("🔔 Attiva" if settings.wantsDailyUpdates else "🔕 Disattiva", settings.dailyUpdatesHour),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_dailynotif(message_id))

    elif (button == "settings_daily_plus") or (button == "settings_daily_minus"):
        hoursplit = settings.dailyUpdatesHour.split(":")
        h = hoursplit[0]
        m = hoursplit[1]
        if "plus" in button:
            if m == "00":
                m = "30"
            elif m == "30":
                m = "00"
                h = "0" if h == "23" else str(int(h) + 1)
        else:
            if m == "00":
                m = "30"
                h = "23" if h == "0" else str(int(h) - 1)
            elif m == "30":
                m = "00"

        settings.dailyUpdatesHour = "{0}:{1}".format(h, m)
        bot.editMessageText((chatId, message_id), "<b>Preferenze notifiche giornaliere</b>\n"
                                                  "- Stato attuale: {0}\n"
                                                  "- Orario notifiche: {1}\n\n"
                                                  "Vuoi che ti dica ogni giorno i compiti per il giorno successivo e le lezioni svolte?"
                                                  "".format("🔔 Attiva" if settings.wantsDailyUpdates else "🔕 Disattiva", settings.dailyUpdatesHour),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_dailynotif(message_id))

    elif button == "logout_yes":
        clearUserData(user)
        bot.editMessageText((chatId, message_id), "😯 Fatto, sei stato disconnesso!\n"
                                                  "Premi /login per entrare di nuovo.\n\n"
                                                  "Premi /help se serve aiuto.", reply_markup=None)

    elif button == "logout_no":
        bot.editMessageText((chatId, message_id), "<i>Logout annullato.</i>", parse_mode="HTML", reply_markup=None)

    elif userLogin(user):

        if (button == "lezioni_prima") or (button == "lezioni_dopo"):
            selectedDay = int(query_split[2]) - 1 if "prima" in button else int(query_split[2]) + 1
            dateformat = (datetime.now() + timedelta(days=selectedDay)).strftime("%d/%m/%Y")
            try:
                data = resp.parseLezioni(api.lezioni(selectedDay))
                bot.editMessageText((chatId, message_id), "📚 <b>Lezioni del {0}</b>:\n\n{1}".format(dateformat, data),
                                    parse_mode="HTML", reply_markup=keyboards.lezioni(message_id, selectedDay))
            except ApiServerError:
                bot.editMessageText((chatId, message_id), "⚠️ I server di ClasseViva non sono raggiungibili.\n"
                                                          "Riprova tra qualche minuto.", reply_markup=None)

        userLogout()


bot.message_loop({'chat': reply, 'callback_query': button_press})

while True:
    sleep(60)
    minute = datetime.now().minute
    if minute % 30 == 0:
        runDailyUpdates(minute)
        runUpdates()
