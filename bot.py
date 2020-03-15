# Python Libraries
from time import sleep
from telepot import Bot, glance
from threading import Thread
from pony.orm import db_session, select, commit
from datetime import datetime, timedelta
from telepot.exception import TelegramError, BotWasBlockedError

# Custom Modules
from modules import parser, keyboards
from modules.crypter import crypt_password
from modules.helpers import *
from modules.database import User, Data, ParsedData, Settings
from modules.api import ClasseVivaAPI, ApiServerError

try:
    f = open('token.txt', 'r')
    token = f.readline().strip()
    f.close()
except FileNotFoundError:
    token = input(" * Incolla qui il token di BotFather: ")
    f = open('token.txt', 'w')
    f.write(token)
    f.close()

bot = Bot(token)
setBot(token)
updatesEvery = 30 # minutes


@db_session
def runUserUpdate(chatId, long_fetch, crhour):
    api = ClasseVivaAPI()
    if userLogin(chatId, api, _quiet=True):
        userdata = Data.get(chatId=chatId)
        settings = Settings.get(chatId=chatId)
        try:
            data = fetchStrict(api)
        except ApiServerError:
            return

        if settings.wantsNotifications is True:
            if (settings.doNotDisturb is False) or (crhour in range(7, 21)):
                dataDidattica = parser.parseNewDidattica(userdata.didattica, data['didattica'])
                dataNote = parser.parseNewNote(userdata.note, data['note'])
                dataVoti = parser.parseNewVoti(userdata.voti, data['voti'], chatId)
                dataAgenda = parser.parseNewAgenda(userdata.agenda, data['agenda'])
                dataCircolari = parser.parseNewCircolari(userdata.circolari, data['circolari'])
                try:
                    if dataDidattica and ("didattica" in settings.activeNews):
                        bot.sendMessage(chatId, "🔔 <b>Nuovi file caricati!</b>"
                                                "{0}".format(dataDidattica), parse_mode="HTML", disable_web_page_preview=True)
                    if dataNote and ("note" in settings.activeNews):
                        bot.sendMessage(chatId, "🔔 <b>Hai nuove note!</b>"
                                                "{0}".format(dataNote), parse_mode="HTML", disable_web_page_preview=True)
                    if dataVoti and ("voti" in settings.activeNews):
                        bot.sendMessage(chatId, "🔔 <b>Hai nuovi voti!</b>"
                                                "{0}".format(dataVoti), parse_mode="HTML", disable_web_page_preview=True)
                    if dataAgenda and ("agenda" in settings.activeNews):
                        bot.sendMessage(chatId, "🔔 <b>Hai nuovi impegni!</b>\n"
                                                "{0}".format(dataAgenda), parse_mode="HTML", disable_web_page_preview=True)
                    if dataCircolari and ("circolari" in settings.activeNews):
                        bot.sendMessage(chatId, "🔔 <b>Hai nuove circolari!</b>"
                                                "{0}".format(dataCircolari), parse_mode="HTML", disable_web_page_preview=True)

                    updateUserdata(chatId, data)
                    fetchAndStore(chatId, api, data, long_fetch)
                except BotWasBlockedError:
                    clearUserData(chatId)
                except TelegramError:
                    pass


@db_session
def runUpdates(long_fetch=False):
    crhour = datetime.now().hour
    pendingUsers = select(user.chatId for user in User if user.password != "")[:]
    for currentUser in pendingUsers:
        Thread(target=runUserUpdate, args=[currentUser, long_fetch, crhour]).start()


@db_session
def runUserDaily(chatId, crhour, crminute, dayString):
    settings = Settings.get(chatId=chatId)
    if settings.wantsDailyUpdates:
        hoursplit = settings.dailyUpdatesHour.split(":")
        if (int(hoursplit[0]) == crhour) and (int(hoursplit[1]) == crminute):
            stored = ParsedData.get(chatId=chatId)
            if (stored.domani != "🗓 Non hai compiti per domani.") or (stored.lezioni != "🎈 Nessuna lezione, per oggi."):
                try:
                    bot.sendMessage(chatId, "🕙 <b>Promemoria!</b>\n\n"
                                            "📆 <b>Cosa devi fare per {0}</b>:\n\n"
                                            "{1}\n\n\n"
                                            "📚 <b>Le lezioni di oggi</b>:\n\n"
                                            "{2}".format(dayString, stored.domani, stored.lezioni), parse_mode="HTML")
                except BotWasBlockedError:
                    clearUserData(chatId)
                except TelegramError:
                    pass


@db_session
def runDailyUpdates(crminute):
    crhour = datetime.now().hour
    isSaturday = datetime.now().isoweekday() == 6
    dayString = "lunedì" if isSaturday else "domani"
    pendingUsers = select(user.chatId for user in User if user.password != "")[:]
    for currentUser in pendingUsers:
        Thread(target=runUserDaily, args=[currentUser, crhour, crminute, dayString]).start()


@db_session
def reply(msg):
    chatId = msg['chat']['id']
    name = msg['from']['first_name']
    if "text" in msg:
        text = msg['text']
    else:
        bot.sendMessage(chatId, "🤨 Formato file non supportato. /help")
        return

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
    
    if text == "/about":
        bot.sendMessage(chatId, "ℹ️ <b>Informazioni sul bot</b>\n"
                                "ClasseVivaBot è un bot creato e sviluppato da Filippo Pesavento, che ti può aiutare "
                                "durante l'anno scolastico mandando notifiche per le novità del registro e molto altro.\n"
                                "Prova ad usarlo per scoprire quanto è comodo!\n\n"
                                "<b>Sviluppo:</b> Filippo Pesavento, Francesco De Benedittis e Gianluca Parri\n"
                                "<b>Hosting:</b> Filippo Pesavento\n\n"
                                "<b>Info sicurezza:</b> /aboutprivacy", parse_mode="HTML")

    elif text == "/aboutprivacy":
        bot.sendMessage(chatId, "ℹ️ <b>Informazioni sulla privacy</b>\n"
                                "La mia password è al sicuro? 🤔\n\n"
                                "🔐 <b>Sì: la tua password viene criptata.</b>\n"
                                "Il bot conserva la tua password in maniera sicura, salvandola in un formato non leggibile da "
                                "persone estranee. Sei al sicuro: i tuoi dati non verranno visti nè rubati da nessuno!\n\n"
                                "🔐 <b>Spiegazione dettagliata:</b>\n"
                                "Tecnicamente potrei decriptare a mano le password e vederle, ma sostanzialmente è complicato, "
                                "perchè il bot genera una chiave per l'algoritmo (visto che il cripting deve essere reversibile, "
                                "per poter mandare le notifiche automatiche) prendendo come dati una chiave comune (che salvo nella RAM "
                                "e inserisco ad ogni avvio, per evitare che qualcuno che non sia io possa leggere il database e i dati degli utenti) "
                                "e anche l'username dell'utente. Quindi ogni utente ha la propria password criptata con una chiave diversa da tutti "
                                "gli altri, e sarebbe difficile anche per me risalire alla password, dovendo sapere di chi è l'username collegato a "
                                "quella password specifica.\n"
                                "Questo non vuol dire che non possa farlo: con un po' di lavoro ci riuscirei. Quindi alla fine devi decidere tu: "
                                "io ti posso assicurare che non leggerò mai nè proverò mai a decriptare le password, sia per un discorso di etica "
                                "che per scelta personale, ma non sono tuo amico nè tuo conoscente: quindi se decidi di non fidarti di uno sconosciuto "
                                "che ti scrive su Telegram (ti posso capire benissimo) sei libero di non usare il bot 🙂\n\n"
                                "<a href=\"https://kutt.it/botinfo\">Altre info & Privacy Policy</a>\n"
                                "<a href=\"https://t.me/pesaventofilippo\">Contattami</a>\n\n"
                                "<i>Se sei venuto qui prima di digitare la password per il login, scrivila adesso!</i>", parse_mode="HTML", disable_web_page_preview=True)


    elif user.status != "normal":
        if text == "/annulla":
            user.status = "normal"
            bot.sendMessage(chatId, "Comando annullato!")

        elif user.status == "login_0":
            if len(text) < 5:
                bot.sendMessage(chatId, "⚠️ Errore: l'username è troppo corto. Riprova!")
                return
            user.username = text
            user.status = "login_1"
            bot.sendMessage(chatId, "👍 Ottimo. Adesso inviami la password.\n"
                                    "Ricorda che la password viene salvata solo per te e viene criptata, nessuno potrà leggerla.\n\n"
                                    "Sei preoccupato per la sicurezza della password? /aboutprivacy")

        elif user.status == "login_1":
            user.password = crypt_password(text, chatId)
            user.status = "normal"
            commit()
            api = ClasseVivaAPI()

            try:
                api.login(user.username, decrypt_password(chatId))
            except ApiServerError:
                try:
                    bot.sendMessage(chatId, "⚠️ I server di ClasseViva non sono raggiungibili.\n"
                                            "Riprova tra qualche minuto.")
                except (TelegramError, BotWasBlockedError):
                    pass
                return
            except Exception:
                clearUserData(chatId)
                try:
                    bot.sendMessage(chatId, "😯 Le tue credenziali di accesso sono errate.\n"
                                            "Effettua nuovamente il /login per favore.")
                except (TelegramError, BotWasBlockedError):
                    pass
                return

            bot.sendMessage(chatId, "Fatto 😊\n"
                                    "Premi /help per vedere la lista dei comandi disponibili.")
            sent = bot.sendMessage(chatId, "🔍 Aggiorno il profilo...")
            data = fetchStrict(api)
            updateUserdata(chatId, data)
            fetchAndStore(chatId, api, data, fetch_long=True)
            bot.editMessageText((chatId, sent['message_id']), "✅ Profilo aggiornato!")
            
        elif user.status == "calling_support":
            user.status = "normal"
            for a in isAdmin():
                bot.sendMessage(a, "🆘 <b>Richiesta di aiuto</b>\n"
                                    "Da: <a href=\"tg://user?id={0}\">{1}</a>\n"
                                    "{2}\n"
                                    "<i>Rispondi al messaggio per parlare con l'utente.</i>".format(chatId, name, "♦️ Beta Tester\n" if user.isBetaTester else ""), parse_mode="HTML")
                bot.forwardMessage(a, chatId, msg['message_id'])
            bot.sendMessage(chatId, "<i>Richiesta inviata.</i>\n"
                                    "Un admin ti risponderà il prima possibile.", parse_mode="HTML")


    elif text == "/help":
        bot.sendMessage(chatId, "Ciao, sono il bot di <b>ClasseViva</b>! 👋🏻\n"
                                "Posso aiutarti a <b>navigare</b> nel registro e posso mandarti <b>notifiche</b> quando hai nuovi avvisi.\n\n"
                                "<b>Lista dei comandi</b>:\n"
                                "- /login - Effettua il login\n"
                                "- /logout - Disconnettiti\n"
                                "- /aggiorna - Aggiorna manualmente tutti i dati, per controllare se ci sono nuovi avvisi.\n"
                                "Oppure, puoi lasciarlo fare a me ogni mezz'ora :)\n"
                                "- /promemoria - Vedi un promemoria con i compiti da fare per domani e le lezioni svolte oggi.\n"
                                "- /agenda - Visualizza agenda (compiti e verifiche)\n"
                                "- /domani - Vedi i compiti che hai per domani\n"
                                "- /assenze - Visualizza assenze, ritardi e uscite anticipate\n"
                                "- /didattica - Visualizza la lista dei file in didattica\n"
                                "- /lezioni - Visualizza la lista delle lezioni\n"
                                "- /voti - Visualizza la lista dei voti\n"
                                "- /note - Visualizza la lista delle note\n"
                                "- /circolari - Visualizza le circolari da leggere\n"
                                "- /info - Visualizza le tue info utente\n"
                                "- /prof - Visualizza la lista delle materie e dei prof\n"
                                "- /settings - Modifica le impostazioni personali del bot\n"
                                "- /about - Informazioni sul bot\n"
                                "- /aboutprivacy - Più informazioni sulla privacy\n"
                                "- /support - Contatta lo staff (emergenze)\n\n"
                                "<b>Notifiche</b>: ogni mezz'ora, se vuoi, ti invierò un messaggio se ti sono arrivati nuovi voti, note, compiti, materiali, avvisi o circolari.\n"
                                "<b>Impostazioni</b>: con /settings puoi cambiare varie impostazioni, tra cui l'orario delle notifiche, quali notifiche ricevere e se riceverle di notte."
                                "", parse_mode="HTML")

    elif text.startswith("/broadcast ") and isAdmin(chatId):
        bdText = text.split(" ", 1)[1]
        pendingUsers = select(u.chatId for u in User)[:]
        userCount = len(pendingUsers)
        for u in pendingUsers:
            try:
                bot.sendMessage(u, bdText, parse_mode="HTML", disable_web_page_preview=True)
            except (TelegramError, BotWasBlockedError):
                userCount -= 1
        bot.sendMessage(chatId, "📢 Messaggio inviato correttamente a {0} utenti!".format(userCount))

    elif text.startswith("/sendmsg ") and isAdmin(chatId):
        selId = int(text.split(" ", 2)[1])
        selText = str(text.split(" ", 2)[2])
        bot.sendMessage(selId, selText, parse_mode="HTML")
        bot.sendMessage(chatId, selText + "\n\n- Messaggio inviato!", parse_mode="HTML")

    elif text == "/globalupdate" and isAdmin(chatId):
        bot.sendMessage(chatId, "🕙 Inizio aggiornamento globale...")
        runUpdates(long_fetch=True)
        bot.sendMessage(chatId, "✅ Aggiornamento globale completato!")

    elif text == "/users" and isAdmin(chatId):
        totalUsers = len(select(u for u in User)[:])
        loggedUsers = len(select(u for u in User if u.password != "")[:])
        bot.sendMessage(chatId, "👤 Utenti totali: <b>{}</b>\n"
                                "👤 Utenti loggati: <b>{}</b>".format(totalUsers, loggedUsers), parse_mode="HTML")

    elif "reply_to_message" in msg:
        if isAdmin(chatId):
            try:
                userId = msg['reply_to_message']['forward_from']['id']
                bot.sendMessage(userId, "💬 <b>Risposta dello staff</b>\n"
                                        "{0}".format(text), parse_mode="HTML")
                bot.sendMessage(chatId, "Risposta inviata!")
            except Exception:
                pass
        else:
            bot.sendMessage(chatId, "Premi /support per parlare con lo staff.")

    elif text == "/annulla":
        bot.sendMessage(chatId, "😴 Nessun comando da annullare!")

    elif hasStoredCredentials(chatId):
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
            sendLongMessage(chatId, "📚 <b>Files caricati in didadttica</b>:\n\n"
                                    "{0}".format(stored.didattica), parse_mode="HTML", disable_web_page_preview=True)

        elif text == "/info":
            bot.sendMessage(chatId, "ℹ️ <b>Ecco le tue info</b>:\n\n"
                                    "{0}".format(stored.info), parse_mode="HTML")

        elif text == "/prof":
            sendLongMessage(chatId, "📚 <b>Lista materie e prof</b>:\n\n"
                                    "{0}".format(stored.prof), parse_mode="HTML")

        elif text == "/note":
            sendLongMessage(chatId, "❗️<b>Le tue note</b>:\n\n"
                                    "{0}".format(stored.note), parse_mode="HTML")

        elif text == "/voti":
            sendLongMessage(chatId, "📝 <b>I tuoi voti</b>:\n\n"
                                    "{0}".format(stored.voti), parse_mode="HTML")

        elif text == "/assenze":
            sendLongMessage(chatId, "{0}".format(stored.assenze), parse_mode="HTML")

        elif text == "/agenda":
            bot.sendMessage(chatId, "📆 <b>Agenda compiti per le prossime 2 settimane</b>:\n\n"
                                    "{0}".format(stored.agenda), parse_mode="HTML", disable_web_page_preview=True)

        elif text == "/domani":
            isSaturday = datetime.now().isoweekday() == 6
            dayString = "lunedì" if isSaturday else "domani"
            bot.sendMessage(chatId, "📆 <b>Compiti e verifiche per {0}</b>:\n\n"
                                    "{1}".format(dayString, stored.domani), parse_mode="HTML", disable_web_page_preview=True)

        elif text == "/circolari":
            bot.sendMessage(chatId, "📩 <b>Circolari da leggere</b>:\n\n"
                                    "{0}".format(stored.circolari), parse_mode="HTML", disable_web_page_preview=True)

        elif text == "/lezioni":
            sent = bot.sendMessage(chatId, "📚 <b>Lezioni di oggi</b>:\n\n"
                                            "{0}".format(stored.lezioni), parse_mode="HTML", reply_markup=None, disable_web_page_preview=True)
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
                                    "{1}".format(stored.domani, stored.lezioni), parse_mode="HTML", disable_web_page_preview=True)

        elif text == "/aggiorna":
            sent = bot.sendMessage(chatId, "📙📙📙 Cerco aggiornamenti... 0%")
            api = ClasseVivaAPI()
            bot.editMessageText((chatId, sent['message_id']), "📗📙📙 Cerco aggiornamenti... 10%")

            if userLogin(chatId, api):
                try:
                    data = fetchStrict(api)
                except ApiServerError:
                    bot.sendMessage(chatId, "⚠️ I server di ClasseViva non sono raggiungibili.\n"
                                            "Riprova tra qualche minuto.")
                    userLogout(api)
                    return
                bot.editMessageText((chatId, sent['message_id']), "📗📙📙 Cerco aggiornamenti... 25%")
                dataDidattica = parser.parseNewDidattica(userdata.didattica, data['didattica'])
                bot.editMessageText((chatId, sent['message_id']), "📗📙📙  Cerco aggiornamenti... 40%")
                dataNote = parser.parseNewNote(userdata.note, data['note'])
                bot.editMessageText((chatId, sent['message_id']), "📗📗📙 Cerco aggiornamenti... 55%")
                dataVoti = parser.parseNewVoti(userdata.voti, data['voti'], chatId)
                bot.editMessageText((chatId, sent['message_id']), "📗📗📙 Cerco aggiornamenti... 70%")
                dataAgenda = parser.parseNewAgenda(userdata.agenda, data['agenda'])
                bot.editMessageText((chatId, sent['message_id']), "📗📗📙 Cerco aggiornamenti... 85%")
                dataCircolari = parser.parseNewCircolari(userdata.circolari, data['circolari'])
                bot.editMessageText((chatId, sent['message_id']), "📗📗📗  Cerco aggiornamenti... 100%")

                if dataDidattica is not None:
                    bot.sendMessage(chatId, "🔔 <b>Nuovi file caricati!</b>{0}".format(dataDidattica), parse_mode="HTML", disable_web_page_preview=True)

                if dataNote is not None:
                    bot.sendMessage(chatId, "🔔 <b>Hai nuove note!</b>{0}".format(dataNote), parse_mode="HTML")

                if dataVoti is not None:
                    bot.sendMessage(chatId, "🔔 <b>Hai nuovi voti!</b>{0}".format(dataVoti), parse_mode="HTML")

                if dataAgenda is not None:
                    bot.sendMessage(chatId, "🔔 <b>Hai nuovi impegni!</b>\n{0}".format(dataAgenda), parse_mode="HTML", disable_web_page_preview=True)

                if dataCircolari is not None:
                    bot.sendMessage(chatId, "🔔 <b>Hai nuove circolari!</b>{0}".format(dataCircolari), parse_mode="HTML", disable_web_page_preview=True)

                if not any([dataDidattica, dataNote, dataVoti, dataAgenda, dataCircolari]):
                    bot.editMessageText((chatId, sent['message_id']), "📗 Dati aggiornati!\n"
                                                                      "📗 Nessuna novità!")
                else:
                    bot.deleteMessage((chatId, sent['message_id']))

                updateUserdata(chatId, data)
                fetchAndStore(chatId, api, data, fetch_long=True)

        elif text == "/support":
            user.status = "calling_support"
            bot.sendMessage(chatId, "🆘 <b>Richiesta di supporto</b>\n"
                                    "Se hai qualche problema che non riesci a risolvere, scrivi qui un messaggio, e un admin "
                                    "ti contatterà il prima possibile.\n\n"
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
    chatId, query_data = glance(msg, flavor="callback_query")[1:3]
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
                                                  "📆 Agenda: {3}\n"
                                                  "📩 Circolari: {4}\n\n"
                                                  "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                  "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "circolari" in settings.activeNews else "🔕 Disattivo"),
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
                                                  "📆 Agenda: {3}\n"
                                                  "📩 Circolari: {4}\n\n"
                                                  "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                  "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "circolari" in settings.activeNews else "🔕 Disattivo"),
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
                                                  "📆 Agenda: {3}\n"
                                                  "📩 Circolari: {4}\n\n"
                                                  "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                  "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "circolari" in settings.activeNews else "🔕 Disattivo"),
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
                                                  "📆 Agenda: {3}\n"
                                                  "📩 Circolari: {4}\n\n"
                                                  "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                  "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "circolari" in settings.activeNews else "🔕 Disattivo"),
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
                                                  "📆 Agenda: {3}\n"
                                                  "📩 Circolari: {4}\n\n"
                                                  "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                  "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "circolari" in settings.activeNews else "🔕 Disattivo"),
                                                    parse_mode="HTML", reply_markup=keyboards.settings_selectnews(message_id))

    elif button == "news_circolari":
        if "circolari" in settings.activeNews:
            settings.activeNews.remove("circolari")
        else:
            settings.activeNews.append("circolari")
        bot.editMessageText((chatId, message_id), "📲 <b>Selezione notifiche</b>\n\n"
                                                  "📚 Didattica: {0}\n"
                                                  "❗️ Note: {1}\n"
                                                  "📝 Voti: {2}\n"
                                                  "📆 Agenda: {3}\n"
                                                  "📩 Circolari: {4}\n\n"
                                                  "Quali notifiche vuoi ricevere? (Clicca per cambiare)"
                                                  "".format("🔔 Attivo" if "didattica" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "note" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "voti" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "agenda" in settings.activeNews else "🔕 Disattivo",
                                                            "🔔 Attivo" if "circolari" in settings.activeNews else "🔕 Disattivo"),
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
        clearUserData(chatId)
        bot.editMessageText((chatId, message_id), "😯 Fatto, sei stato disconnesso!\n"
                                                  "Premi /login per entrare di nuovo.\n\n"
                                                  "Premi /help se serve aiuto.", reply_markup=None)

    elif button == "logout_no":
        bot.editMessageText((chatId, message_id), "<i>Logout annullato.</i>", parse_mode="HTML", reply_markup=None)

    elif (button == "lezioni_prima") or (button == "lezioni_dopo"):
        api = ClasseVivaAPI()
        if userLogin(chatId, api):
            selectedDay = int(query_split[2]) - 1 if "prima" in button else int(query_split[2]) + 1
            dateformat = (datetime.now() + timedelta(days=selectedDay)).strftime("%d/%m/%Y")
            try:
                apiRes = api.lezioni(selectedDay)
                data = parser.parseLezioni(apiRes)
                bot.editMessageText((chatId, message_id), "📚 <b>Lezioni del {0}</b>:\n\n{1}".format(dateformat, data),
                                    parse_mode="HTML", reply_markup=keyboards.lezioni(message_id, selectedDay), disable_web_page_preview=True)
            except ApiServerError:
                bot.editMessageText((chatId, message_id), "⚠️ I server di ClasseViva non sono raggiungibili.\n"
                                                          "Riprova tra qualche minuto.", reply_markup=None)
            userLogout(api)


def accept_message(msg):
    Thread(target=reply, args=[msg]).start()

def accept_button(msg):
    Thread(target=button_press, args=[msg]).start()

bot.message_loop({'chat': accept_message, 'callback_query': accept_button})


while True:
    sleep(60)
    minute = datetime.now().minute
    if minute % updatesEvery == 0:
        runDailyUpdates(minute)
        runUpdates()
