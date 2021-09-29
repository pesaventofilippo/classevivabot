# Python Libraries
from time import sleep
from telepotpro import Bot
from telepotpro.exception import TelegramError, BotWasBlockedError
from threading import Thread, Lock
from pony.orm import db_session, select, commit
from datetime import datetime, timedelta
from json import load as jsload
from os.path import abspath, dirname, join

# Custom Modules
from modules import parsers, keyboards, helpers
from modules.crypter import crypt_password, decrypt_password
from modules.database import User, Data, ParsedData, Settings, Document
from modules.api import ClasseVivaAPI, ApiServerError, FileNotOwnedError

with open(join(dirname(abspath(__file__)), "settings.json")) as settings_file:
    js_settings = jsload(settings_file)

bot = Bot(js_settings["token"])
updatesEvery = js_settings["updateEveryMin"]
restrictedMode = js_settings["restrictedMode"]
updateLock = Lock()


@db_session(retry=3)
def runUserUpdate(chatId, long_fetch, runDatetime, sendMessages=True):
    api = ClasseVivaAPI()
    if helpers.userLogin(chatId, api, _quiet=True):
        userdata = Data.get(chatId=chatId)
        settings = Settings.get(chatId=chatId)
        try:
            data = helpers.fetchStrict(api)
        except ApiServerError:
            return

        if settings.wantsNotifications:
            if (not settings.doNotDisturb) or (runDatetime.hour in range(7, 21)):
                dataDidattica = parsers.parseNewDidattica(userdata.didattica, data['didattica'])
                dataNote = parsers.parseNewNote(userdata.note, data['note'])
                dataVoti = parsers.parseNewVoti(userdata.voti, data['voti'], chatId)
                dataAgenda = parsers.parseNewAgenda(userdata.agenda, data['agenda'], chatId)
                dataCircolari = parsers.parseNewCircolari(userdata.circolari, data['circolari'])
                if sendMessages:
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
                    except BotWasBlockedError:
                        helpers.clearUserData(chatId)
                        return
                    except TelegramError:
                        pass
                helpers.updateUserdata(chatId, data)
                helpers.fetchAndStore(chatId, api, data, long_fetch)
        user = User.get(chatId=chatId)
        user.remainingCalls = 3


@db_session(retry=3)
def runUpdates(long_fetch=False, sendMessages=True):
    childThreads = []
    if not updateLock.acquire(blocking=True, timeout=60): return

    runDatetime = datetime.now()
    pendingUsers = helpers.isAdmin() if restrictedMode else select(user.chatId for user in User if user.password != "")[:]
    for currentUser in pendingUsers:
        t = Thread(
            target=runUserUpdate,
            name=f"upd_{currentUser}",
            args=[currentUser, long_fetch, runDatetime, sendMessages]
        )
        childThreads.append(t)
        t.start()

    while any(t.is_alive() for t in childThreads):
        sleep(2)
    updateLock.release()


@db_session(retry=3)
def runUserDaily(chatId, runDatetime, dayString):
    settings = Settings.get(chatId=chatId)
    if settings.wantsDailyUpdates:
        seltime = datetime.strptime(settings.dailyUpdatesHour, "%H:%M")
        if (seltime.hour == runDatetime.hour) and (seltime.minute == runDatetime.minute):
            stored = ParsedData.get(chatId=chatId)
            if (stored.domani != "🗓 Non hai compiti per domani.") or (stored.lezioni != "🎈 Nessuna lezione, per oggi."):
                try:
                    bot.sendMessage(chatId, "🕙 <b>Promemoria!</b>\n\n"
                                            "📆 <b>Cosa devi fare per {0}</b>:\n\n"
                                            "{1}\n\n\n"
                                            "📚 <b>Le lezioni di oggi</b>:\n\n"
                                            "{2}".format(dayString, stored.domani, stored.lezioni), parse_mode="HTML")
                except BotWasBlockedError:
                    helpers.clearUserData(chatId)
                except TelegramError:
                    pass


@db_session(retry=3)
def runDailyUpdates(runDatetime):
    childThreads = []
    if not updateLock.acquire(blocking=True, timeout=60): return

    isSaturday = runDatetime.isoweekday() == 6
    dayString = "lunedì" if isSaturday else "domani"
    pendingUsers = helpers.isAdmin() if restrictedMode else select(user.chatId for user in User if user.password != "")[:]
    for currentUser in pendingUsers:
        t = Thread(
            target=runUserDaily,
            name=f"mem_{currentUser}",
            args=[currentUser, runDatetime, dayString]
        )
        childThreads.append(t)
        t.start()

    while any(t.is_alive() for t in childThreads):
        sleep(2)
    updateLock.release()


@db_session
def sendFile(chatId: int, desc: str, *args):
    sent = bot.sendMessage(chatId, f"⬇️ <i>Download {desc} in corso...</i>", parse_mode="HTML")
    msgIdent = (chatId, sent['message_id'])
    api = ClasseVivaAPI()
    getFunc = api.getCirc if desc == "circolare" else api.getFile

    if helpers.userLogin(chatId, api):
        try:
            if desc != "link":
                toSend, fileName = getFunc(*args)
                bot.sendDocument(chatId, (fileName, toSend))
                bot.deleteMessage(msgIdent)
            else:
                link = api.getLink(*args)["item"]["link"]
                bot.editMessageText(msgIdent, f"📎 Link: {link}")
        except FileNotOwnedError:
            bot.editMessageText(msgIdent, "⚠️ Questo file non è tuo, oppure c'è un problema con il server.")
        except (ApiServerError, Exception):
            bot.editMessageText(msgIdent, "⚠️ Non sono riuscito a scaricare il file.")
    else:
        bot.editMessageText(msgIdent, "⚠️ Errore nel login.")


@db_session(retry=3)
def reply(msg):
    global restrictedMode
    chatId = msg['chat']['id']
    name = msg['from']['first_name']
    text = msg.get("text", "")

    if chatId < 0:
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

    if (not restrictedMode) or helpers.isAdmin(chatId):
        if text == "/about":
            bot.sendMessage(chatId, "ℹ️ <b>Informazioni sul bot</b>\n"
                                    "ClasseVivaBot è un bot creato e sviluppato da Filippo Pesavento, che ti può aiutare "
                                    "durante l'anno scolastico mandando notifiche per le novità del registro e molto altro.\n"
                                    "Prova ad usarlo per scoprire quanto è comodo!\n\n"
                                    "<b>Sviluppo:</b> <a href=\"https://t.me/pesaventofilippo\">Filippo Pesavento</a> e Francesco De Benedittis\n"
                                    "<b>Contributori:</b> Gianluca Parri e PolpOnline\n"
                                    "<b>Hosting:</b> Filippo Pesavento\n\n"
                                    "<b>Info sicurezza:</b> /aboutprivacy", parse_mode="HTML", disable_web_page_preview=True)

        elif text == "/aboutprivacy":
            bot.sendMessage(chatId, "ℹ️ <b>Informazioni sulla privacy</b>\n"
                                    "La mia password è al sicuro? 🤔\n\n"
                                    "🔐 <b>Sì: la tua password viene criptata.</b>\n"
                                    "Il bot conserva la tua password in maniera sicura, salvandola in un formato non leggibile da "
                                    "persone estranee. Sei al sicuro: i tuoi dati non verranno visti nè rubati da nessuno!\n\n"
                                    "🔐 <b>Spiegazione dettagliata:</b>\n"
                                    "Tecnicamente potrei decriptare a mano le password e vederle, ma sostanzialmente è complicato, "
                                    "perchè il bot genera una chiave per l'algoritmo (visto che il cripting deve essere reversibile, "
                                    "per poter mandare le notifiche automatiche) prendendo come dati una chiave comune (che salvo nella RAM, "
                                    "per evitare che qualcuno che non sia io possa leggere il database e i dati degli utenti) "
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
                    helpers.clearUserData(chatId)
                    try:
                        bot.sendMessage(chatId, "😯 Le tue credenziali di accesso sono errate.\n"
                                                "Effettua nuovamente il /login per favore.")
                    except (TelegramError, BotWasBlockedError):
                        pass
                    return

                bot.sendMessage(chatId, "Fatto 😊\n"
                                        "Premi /help per vedere la lista dei comandi disponibili.")
                sent = bot.sendMessage(chatId, "🔍 Aggiorno il profilo...")
                data = helpers.fetchStrict(api)
                helpers.updateUserdata(chatId, data)
                helpers.fetchAndStore(chatId, api, data, fetch_long=True)
                bot.editMessageText((chatId, sent['message_id']), "✅ Profilo aggiornato!")

            elif user.status == "calling_support":
                user.status = "normal"
                for a in helpers.isAdmin():
                    bot.sendMessage(a, "🆘 <b>Richiesta di aiuto</b>\n"
                                       "Da: <a href=\"tg://user?id={0}\">{1}</a>\n\n"
                                       "<i>Rispondi al messaggio per parlare con l'utente.</i>".format(chatId, name),
                                    parse_mode="HTML")
                    if "reply_to_message" in msg:
                        bot.forwardMessage(a, chatId, msg["reply_to_message"]["message_id"])
                    bot.forwardMessage(a, chatId, msg['message_id'], disable_notification=True)
                bot.sendMessage(chatId, "<i>Richiesta inviata.</i>\n"
                                        "Un admin ti risponderà il prima possibile.", parse_mode="HTML")

            elif user.status == "sending_orario":
                if msg.get("photo"):
                    fileId = msg.get("photo")[0]["file_id"]
                    ext = "photo"
                elif msg.get("document"):
                    fileId = msg.get("document")["file_id"]
                    ext = "document"
                else:
                    bot.sendMessage(chatId, "🤔 Documento non valido. Invia una foto o un file.\n"
                                            "Premi /annulla per annullare.")
                    return

                if not Document.exists(lambda d: (d.chatId == chatId and d.type == "orario")):
                    Document(chatId=chatId, type="orario", data={"fileId": fileId, "ext": ext})
                else:
                    doc = Document.get(chatId=chatId, type="orario")
                    doc.data = {"fileId": fileId, "ext": ext}
                bot.sendMessage(chatId, "✅ Orario impostato!\n"
                                        "Richiamalo con /orario.")
                user.status = "normal"

            elif user.status == "memo_date":
                if not text:
                    bot.sendMessage(chatId, "Inviami la data in formato GG/MM.\n"
                                            "Premi /annulla per annullare.")
                    return

                try:
                    now = datetime.now()
                    when = datetime.strptime(text, "%d/%m")
                    when.replace(year=now.year)

                    if when < now:
                        when.replace(year=now.year+1)
                    if when > now + timedelta(days=28):
                        bot.sendMessage(chatId, "⚠️ Data non valida.\n"
                                                "La data non può essere oggi, nel passato oppure fra più di 4 settimane.\n"
                                                "Premi /annulla per annullare.")
                        return

                    memoDate = when.strftime("%d/%m/%Y")
                    user.status = f"memo_text#{memoDate}"

                    bot.sendMessage(chatId, f"💡 <b>Data memo: {memoDate}</b>\n"
                                            f"Inviami il testo del memo, o premi /annulla per annullare.",
                                    parse_mode="HTML")
                except ValueError:
                    bot.sendMessage(chatId, "⚠️ Data non valida.\n"
                                            "Inviami la data in formato GG/MM.\n"
                                            "Premi /annulla per annullare.")

            elif user.status.startswith("memo_text"):
                if not text or len(text) > 400:
                    bot.sendMessage(chatId, "⚠️ Inviami il testo della memo (max. 400 caratteri).\n"
                                            "Premi /annulla per annullare.")
                    return

                memoDate = user.status.split("#")[1]
                memo = Document(chatId=chatId, type="memo", data={
                    "date": memoDate,
                    "text": text
                })
                bot.sendMessage(chatId, f"✅ Ho creato la memo per il <b>{memo.data['date']}</b>:\n"
                                        f"{memo.data['text']}", parse_mode="HTML")


        elif text == "/help":
            bot.sendMessage(chatId, "Ciao, sono il bot di <b>ClasseViva</b>! 👋🏻\n"
                                    "Posso aiutarti a <b>navigare</b> nel registro e posso mandarti <b>notifiche</b> quando hai nuovi avvisi.\n\n"
                                    "<b>Lista dei comandi</b>:\n"
                                    "- /login - Effettua il login\n"
                                    "- /aggiorna - Aggiorna manualmente tutti i dati, per controllare se ci sono nuovi avvisi.\n"
                                    "Oppure, puoi lasciarlo fare a me ogni mezz'ora :)\n"
                                    "- /agenda - Visualizza agenda (compiti e verifiche)\n"
                                    "- /domani - Vedi i compiti che hai per domani\n"
                                    "- /promemoria - Vedi un promemoria con i compiti da fare per domani e le lezioni svolte oggi.\n"
                                    "- /memo - Aggiungi un memo all'agenda\n"
                                    "- /voti - Visualizza la lista dei voti\n"
                                    "- /lezioni - Visualizza la lista delle lezioni\n"
                                    "- /didattica - Visualizza la lista dei file in didattica\n"
                                    "- /circolari - Visualizza le circolari da leggere\n"
                                    "- /orario - Imposta o visualizza l'orario delle lezioni\n"
                                    "- /settings - Modifica le impostazioni personali del bot\n"
                                    "- /assenze - Visualizza assenze, ritardi e uscite anticipate\n"
                                    "- /note - Visualizza la lista delle note\n"
                                    "- /info - Visualizza le tue info utente\n"
                                    "- /prof - Visualizza la lista delle materie e dei prof\n"
                                    "- /about - Informazioni sul bot\n"
                                    "- /aboutprivacy - Più informazioni sulla privacy\n"
                                    "- /logout - Disconnettiti\n"
                                    "- /support - Contatta lo staff (emergenze)\n\n"
                                    "<b>Notifiche</b>: ogni mezz'ora, se vuoi, ti invierò un messaggio se ti sono arrivati nuovi voti, note, compiti, materiali, avvisi o circolari.\n"
                                    "<b>Impostazioni</b>: con /settings puoi cambiare varie impostazioni, tra cui l'orario delle notifiche, quali notifiche ricevere e se riceverle di notte."
                                    "", parse_mode="HTML")

        elif text.startswith("/broadcast ") and helpers.isAdmin(chatId):
            bdText = text.split(" ", 1)[1]
            pendingUsers = select(u.chatId for u in User)[:]
            userCount = len(pendingUsers)
            for u in pendingUsers:
                try:
                    bot.sendMessage(u, bdText, parse_mode="HTML", disable_web_page_preview=True)
                except (TelegramError, BotWasBlockedError):
                    userCount -= 1
            bot.sendMessage(chatId, "📢 Messaggio inviato correttamente a {0} utenti!".format(userCount))

        elif text.startswith("/sendmsg ") and helpers.isAdmin(chatId):
            selId = int(text.split(" ", 2)[1])
            selText = str(text.split(" ", 2)[2])
            bot.sendMessage(selId, selText, parse_mode="HTML")
            bot.sendMessage(chatId, selText + "\n\n- Messaggio inviato!", parse_mode="HTML")

        elif text == "/globalupdate" and helpers.isAdmin(chatId):
            bot.sendMessage(chatId, "🕙 Inizio aggiornamento globale...")
            runUpdates(long_fetch=True)
            bot.sendMessage(chatId, "✅ Aggiornamento globale completato!")

        elif text == "/silentupdate" and helpers.isAdmin(chatId):
            bot.sendMessage(chatId, "🕙 [BG] Inizio aggiornamento globale...")
            runUpdates(long_fetch=True, sendMessages=False)
            bot.sendMessage(chatId, "✅ [BG] Aggiornamento globale completato!")

        elif text == "/users" and helpers.isAdmin(chatId):
            totalUsers = len(select(u for u in User)[:])
            loggedUsers = len(select(u for u in User if u.password != "")[:])
            bot.sendMessage(chatId, "👤 Utenti totali: <b>{}</b>\n"
                                    "👤 Utenti loggati: <b>{}</b>".format(totalUsers, loggedUsers), parse_mode="HTML")

        elif text == "/restrict" and helpers.isAdmin(chatId):
            restrictedMode = True
            bot.sendMessage(chatId, "<i>Modalità ristretta attiva.\n"
                                    "Solo gli admin possono usare il bot.</i>", parse_mode="HTML")

        elif text == "/unrestrict" and helpers.isAdmin(chatId):
            restrictedMode = False
            bot.sendMessage(chatId, "<i>Modalità ristretta disattivata.\n"
                                    "Tutti gli utenti potranno usare il bot.</i>", parse_mode="HTML")

        elif "reply_to_message" in msg:
            if helpers.isAdmin(chatId):
                try:
                    userId = msg['reply_to_message']['forward_from']['id']
                    bot.sendMessage(userId, "💬 <b>Risposta dello staff</b>\n"
                                            "{0}".format(text), parse_mode="HTML")
                    bot.sendMessage(chatId, "Risposta inviata!")
                except Exception:
                    bot.sendMessage(chatId, "Errore nell'invio.")
            else:
                if text.lower() == "no":
                    bot.sendMessage(chatId, "<i>Ah ok, scusa.</i>", parse_mode="HTML")
                else:
                    bot.sendMessage(chatId, "Scrivi /support per parlare con lo staff.")

        elif text == "/annulla":
            bot.sendMessage(chatId, "😴 Nessun comando da annullare!")

        elif helpers.hasStoredCredentials(chatId):
            if text == "/start":
                bot.sendMessage(chatId, "Bentornato, <b>{0}</b>!\n"
                                        "Cosa posso fare per te? 😊".format(name), parse_mode="HTML")

            elif text == "/login":
                bot.sendMessage(chatId, "Sei già loggato.\n"
                                        "Premi /logout per uscire.")

            elif text == "/logout":
                bot.sendMessage(chatId, "Tutti i tuoi dati scolastici e le credenziali verranno eliminate dal bot.\n"
                                        "Sei <b>veramente sicuro</b> di voler uscire?",
                                parse_mode="HTML", reply_markup=keyboards.logout())

            elif text == "/didattica":
                helpers.sendLongMessage(chatId, "📚 <b>Files caricati in didattica</b>:\n\n"
                                        "{0}".format(stored.didattica), parse_mode="HTML", disable_web_page_preview=True)

            elif text == "/info":
                bot.sendMessage(chatId, "ℹ️ <b>Ecco le tue info</b>:\n\n"
                                        "{0}".format(stored.info), parse_mode="HTML")

            elif text == "/prof":
                helpers.sendLongMessage(chatId, "📚 <b>Lista materie e prof</b>:\n\n"
                                        "{0}".format(stored.prof), parse_mode="HTML")

            elif text == "/note":
                helpers.sendLongMessage(chatId, "❗️<b>Le tue note</b>:\n\n"
                                        "{0}".format(stored.note), parse_mode="HTML")

            elif text == "/voti":
                helpers.sendLongMessage(chatId, "📝 <b>I tuoi voti</b>:\n\n"
                                        "{0}".format(stored.voti), parse_mode="HTML")

            elif text == "/assenze":
                helpers.sendLongMessage(chatId, "{0}".format(stored.assenze), parse_mode="HTML")

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
                bot.sendMessage(chatId, "📚 <b>Lezioni di oggi</b>:\n\n"
                                        "{0}".format(stored.lezioni),
                                parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboards.lezioni())

            elif text == "/settings":
                bot.sendMessage(chatId, "🛠 <b>Impostazioni</b>\n"
                                        "Ecco le impostazioni del bot. Cosa vuoi modificare?",
                                parse_mode="HTML", reply_markup=keyboards.settings_menu())

            elif text == "/promemoria":
                bot.sendMessage(chatId, "🕙 <b>Promemoria!</b>\n\n"
                                        "📆 <b>Cosa devi fare per domani</b>:\n\n"
                                        "{0}\n\n\n"
                                        "📚 <b>Le lezioni di oggi</b>:\n\n"
                                        "{1}".format(stored.domani, stored.lezioni),
                                parse_mode="HTML", disable_web_page_preview=True)

            elif text == "/aggiorna":
                if (user.remainingCalls > 0) or (helpers.isAdmin(chatId)):
                    if not updateLock.acquire(blocking=False):
                        bot.sendMessage(chatId, "ℹ️ <b>Aspetta!</b>\n"
                                                "Il bot sta già eseguendo degli aggiornamenti globali per tutti gli utenti.",
                                        parse_mode="HTML")
                        return

                    sent = bot.sendMessage(chatId, "📙📙📙 Cerco aggiornamenti... 0%")
                    user.remainingCalls -= 1
                    commit()
                    updateLock.release()
                    bot.editMessageText((chatId, sent['message_id']), "📗📙📙 Cerco aggiornamenti... 10%")
                    api = ClasseVivaAPI()
                    bot.editMessageText((chatId, sent['message_id']), "📗📙📙 Cerco aggiornamenti... 20%")

                    if helpers.userLogin(chatId, api):
                        bot.editMessageText((chatId, sent['message_id']), "📗📙📙 Cerco aggiornamenti... 35%")
                        try:
                            data = helpers.fetchStrict(api)
                        except ApiServerError:
                            bot.editMessageText((chatId, sent['message_id']), "⚠️ I server di ClasseViva non sono raggiungibili.\n"
                                                                              "Riprova tra qualche minuto.")
                            return
                        bot.editMessageText((chatId, sent['message_id']), "📗📗📙 Cerco aggiornamenti... 50%")
                        dataDidattica = parsers.parseNewDidattica(userdata.didattica, data['didattica'])
                        bot.editMessageText((chatId, sent['message_id']), "📗📗📙  Cerco aggiornamenti... 60%")
                        dataNote = parsers.parseNewNote(userdata.note, data['note'])
                        bot.editMessageText((chatId, sent['message_id']), "📗📗📙 Cerco aggiornamenti... 70%")
                        dataVoti = parsers.parseNewVoti(userdata.voti, data['voti'], chatId)
                        bot.editMessageText((chatId, sent['message_id']), "📗📗📙 Cerco aggiornamenti... 80%")
                        dataAgenda = parsers.parseNewAgenda(userdata.agenda, data['agenda'], chatId)
                        bot.editMessageText((chatId, sent['message_id']), "📗📗📙 Cerco aggiornamenti... 90%")
                        dataCircolari = parsers.parseNewCircolari(userdata.circolari, data['circolari'])
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

                        helpers.updateUserdata(chatId, data)
                        helpers.fetchAndStore(chatId, api, data, fetch_long=True)

                else:
                    bot.sendMessage(chatId, "⛔️ Hai usato troppi /aggiorna recentemente. Aspetta un po'!")

            elif (text == "/support") or (text == "/start support"):
                user.status = "calling_support"
                bot.sendMessage(chatId, "🆘 <b>Richiesta di supporto</b>\n"
                                        "Se hai qualche problema che non riesci a risolvere, scrivi qui un messaggio, e un admin "
                                        "ti contatterà il prima possibile.\n\n"
                                        "<i>Per annullare, premi</i> /annulla.", parse_mode="HTML")

            elif text == "/orario":
                if not Document.exists(lambda d: (d.chatId == chatId and d.type == "orario")):
                    user.status = "sending_orario"
                    bot.sendMessage(chatId, "🕑 <b>Impostazione orario</b>\n"
                                            "Inviami un documento (PDF oppure foto) per salvarlo e richiamarlo "
                                            "quando serve con /orario!", parse_mode="HTML")
                else:
                    doc = Document.get(chatId=chatId, type="orario")
                    sendFunc = bot.sendPhoto if doc.data["ext"] == "photo" else bot.sendDocument
                    sendFunc(chatId, doc.data["fileId"], reply_markup=keyboards.mod_orario())

            elif text == "/memo":
                user.status = "memo_date"
                today = datetime.now().weekday()
                bot.sendMessage(chatId, "💡 <b>Memo personale</b>\n"
                                        "Crea un memo personale per aggiungere i compiti da fare all'agenda!\n"
                                        "Inviami <b>la data</b> di consegna, nel formato GG/MM, oppure scegli un'opzione "
                                        "da quelle qui sotto.\n\n"
                                        "Premi /annulla per annullare.",
                                parse_mode="HTML", reply_markup=keyboards.create_memo(today))


            # Custom Start Parameters
            elif text.startswith("/start "):
                param = text.split(' ')[1]
                if param.startswith("circ"):
                    evtCode = param.split("-")[0].replace("circ", "")
                    pubId = int(param.split("-")[1])
                    sendFile(chatId, "circolare", evtCode, pubId)

                elif param.startswith("file"):
                    intId = int(param[4:])
                    sendFile(chatId, "file", intId)

                elif param.startswith("link"):
                    intId = int(param[4:])
                    sendFile(chatId, "link", intId)

            elif text == "⬆️⬆️⬇️⬇️⬅️➡️⬅️➡️🅱️🅰️" or text == "⬆️⬆️⬇️⬇️⬅️➡️⬅️➡️🅱🅰":
                from random import choice
                today = datetime.today().strftime("%d/%m/%Y")
                subject = choice(["MATEMATICA", "ITALIANO", "INGLESE", "STORIA"])
                bot.sendMessage(chatId, "🔔 <b>Hai nuovi voti!</b>\n\n"
                                        "📚 <b>{}</b>\n\n"
                                        "📗 <b>Voto 10</b> • Scritto • {}\n"
                                        "<i>Start!</i>".format(subject, today), parse_mode="HTML")

            # Text is not a keyword
            else:
                bot.sendMessage(chatId, "Non ho capito...\n"
                                        "Serve aiuto? Premi /help")

        # User not logged in
        else:
            if text == "/login":
                user.status = "login_0"
                bot.sendMessage(chatId, "Per favore, inviami il tuo <b>username</b> (quello che usi per accedere al registro).\n"
                                        "Usa /annulla se serve.", parse_mode="HTML")
            else:
                bot.sendMessage(chatId, "Benvenuto, <b>{0}</b>!\n"
                                        "Per utilizzarmi devi eseguire il /login.\n\n"
                                        "Premi /help se serve aiuto.".format(name), parse_mode="HTML")

    # Normal user with restricted mode
    else:
        if text == "/moreinfo":
            bot.sendMessage(chatId, "❓ <b>Che genere di problemi?</b>\n"
                                    "ClasseViva ha recentemente imposto un limite alle sue API, che questo bot utilizza, "
                                    "anche se è nascosto e non sempre uguale. Con l'aumentare degli utenti, il bot doveva fare "
                                    "sempre più richieste e una volta raggiunto il limite ha cominciato a non funzionare più.\n"
                                    "La soluzione sarebbe avere una lista di minimo 20 proxy da utilizzare per fare le richieste "
                                    "(si tratta di max. 200KB di traffico ogni 30 minuti, non è quello il problema), che "
                                    "però è molto difficile da trovare senza pagare qualche servizio, che al momento non posso permettermi.\n\n"
                                    "❔ <b>Posso contattarti?</b>\n"
                                    "Certo, puoi scrivermi per qualsiasi motivo <a href=\"https://t.me/pesaventofilippo\">qui</a> "
                                    "o mandarmi una mail a cvvbot@pesaventofilippo.com.\n"
                                    "Non sono un bot, quindi magari non rispondo subito 🙂", parse_mode="HTML", disable_web_page_preview=True)

        else:
            bot.sendMessage(chatId, "ℹ️ <b>Bot in manutenzione</b>\n"
                                    "Il bot è attualmente in manutenzione per problemi con ClasseViva, e tutte le sue "
                                    "funzioni sono temporaneamente disabilitate.\n"
                                    "Non eliminare questa chat: se vuoi puoi archiviarla su Telegram, così appena "
                                    "ci saranno notizie ti manderò un messaggio.\n\n"
                                    "/moreinfo", parse_mode="HTML")


@db_session(retry=3)
def button_press(msg):
    chatId = msg['message']['chat']['id']
    msgId = msg['message']['message_id']
    text = msg['data']
    msgIdent = (chatId, msgId)

    user = User.get(chatId=chatId)
    settings = Settings.get(chatId=chatId)

    def editNotif():
        bot.editMessageText(msgIdent, "<b>Preferenze notifiche</b>\n"
                                      "- Stato attuale: {0}\n\n"
                                      "Vuoi che ti mandi notifiche se trovo novità?\n"
                                      "<b>Nota</b>: Se non vuoi riceverle di notte, puoi impostarlo a parte."
                                      "".format("🔔 Attivo" if settings.wantsNotifications else "🔕 Spento"),
                            parse_mode="HTML", reply_markup=keyboards.settings_notifications(settings.wantsNotifications))

    def editNotifDaily():
        bot.editMessageText(msgIdent, "<b>Preferenze notifiche giornaliere</b>\n"
                                      "- Stato attuale: {0}\n"
                                      "- Orario notifiche: {1}\n\n"
                                      "Vuoi che ti dica ogni giorno i compiti per il giorno successivo e le lezioni svolte?"
                                      "".format("🔔 Attiva" if settings.wantsDailyUpdates else "🔕 Spenta", settings.dailyUpdatesHour),
                            parse_mode="HTML", reply_markup=keyboards.settings_dailynotif(settings.wantsDailyUpdates))

    def editNotifNight():
        bot.editMessageText(msgIdent, "<b>Preferenze modalità notturna</b>\n"
                                      "- Stato attuale: {0}\n\n"
                                      "Vuoi che silenzi le notifiche nella fascia oraria notturna (21:00 - 7:00)?"
                                      "".format("😴 Attivo" if settings.doNotDisturb else "🔔 Suona"),
                            parse_mode="HTML", reply_markup=keyboards.settings_donotdisturb(settings.doNotDisturb))

    def editNotifSelection():
        stats = ["🔔 Attivo" if type in settings.activeNews else "🔕 Spento"
                 for type in ["didattica", "note", "voti", "agenda", "circolari"]]
        bot.editMessageText(msgIdent, f"📲 <b>Selezione notifiche</b>\n\n"
                                      f"📚 Didattica: {stats[0]}\n"
                                      f"❗️ Note: {stats[1]}\n"
                                      f"📝 Voti: {stats[2]}\n"
                                      f"📆 Agenda: {stats[3]}\n"
                                      f"📩 Circolari: {stats[4]}\n\n"
                                      "Quali notifiche vuoi ricevere? (Clicca per cambiare)",
                            parse_mode="HTML", reply_markup=keyboards.settings_selectnews())

    if (not restrictedMode) or helpers.isAdmin(chatId):
        if text == "settings_main":
            bot.editMessageText(msgIdent, "🛠 <b>Impostazioni</b>\n"
                                          "Ecco le impostazioni del bot. Cosa vuoi modificare?",
                                parse_mode="HTML", reply_markup=keyboards.settings_menu())

        elif text == "settings_close":
            bot.editMessageText(msgIdent, "✅ Impostazioni salvate.", reply_markup=None)

        elif text == "settings_notifications":
            editNotif()

        elif text == "settings_donotdisturb":
            editNotifNight()

        elif text == "settings_dailynotif":
            editNotifDaily()

        elif text == "settings_selectnews":
            editNotifSelection()

        elif text.startswith("news_"):
            cat = text.split("_", 1)[1]
            if cat in settings.activeNews:
                settings.activeNews.remove(cat)
            else:
                settings.activeNews.append(cat)
            editNotifSelection()

        elif text.startswith("settings_notif_"):
            ans = text.endswith("yes")
            settings.wantsNotifications = ans
            editNotif()

        elif text.startswith("settings_night_"):
            ans = text.endswith("yes")
            settings.doNotDisturb = ans
            editNotifNight()

        elif text.startswith("settings_daily_"):
            if text.endswith("yes") or text.endswith("no"):
                ans = text.endswith("yes")
                settings.wantsDailyUpdates = ans
            else:
                seltime = datetime.strptime(settings.dailyUpdatesHour, "%H:%M")
                if text.endswith("plus"):
                    seltime += timedelta(minutes=30)
                else:
                    seltime -= timedelta(minutes=30)
                settings.dailyUpdatesHour = seltime.strftime("%H:%M")
            editNotifDaily()

        elif text.startswith("logout"):
            if text.endswith("yes"):
                helpers.clearUserData(chatId)
                bot.editMessageText(msgIdent, "😯 Fatto, sei stato disconnesso!\n"
                                              "Premi /login per entrare di nuovo.\n\n"
                                              "Premi /help se serve aiuto.", reply_markup=None)
            else:
                bot.editMessageText(msgIdent, "<i>Logout annullato.</i>", parse_mode="HTML", reply_markup=None)

        elif text.startswith("lezioni"):
            api = ClasseVivaAPI()
            if helpers.userLogin(chatId, api):
                newDay = int(text.split("#")[1])
                dateformat = "del" + (datetime.now() + timedelta(days=newDay)).strftime("%d/%m/%Y") \
                             if newDay != 0 else "di oggi"
                try:
                    apiRes = api.lezioni(newDay)
                    data = parsers.parseLezioni(apiRes)
                    bot.editMessageText(msgIdent, f"📚 <b>Lezioni {dateformat}</b>:\n\n"
                                                  f"{data}", parse_mode="HTML", reply_markup=keyboards.lezioni(newDay),
                                        disable_web_page_preview=True)
                except ApiServerError:
                    bot.editMessageText(msgIdent, "⚠️ I server di ClasseViva non sono raggiungibili.\n"
                                                  "Riprova tra qualche minuto.", reply_markup=None)

        elif text.startswith("orario"):
            if text.endswith("del"):
                doc = Document.get(chatId=chatId, type="orario")
                doc.delete()
                bot.editMessageCaption(msgIdent, "🗑 Orario eliminato.", reply_markup=None)

            elif text.endswith("mod"):
                user.status = "sending_orario"
                bot.editMessageReplyMarkup(msgIdent, None)
                bot.sendMessage(chatId, "🕑 <b>Impostazione orario</b>\n"
                                        "Inviami un documento (PDF oppure foto) da impostare come nuovo orario.\n\n"
                                        "Usa /annulla per annullare la modifica.", parse_mode="HTML", reply_markup=None)

        elif user.status == "memo_date" and text.startswith("memo"):
            when = int(text[-1])
            memoDate = (datetime.now() + timedelta(days=when)).strftime("%d/%m/%Y")
            user.status = f"memo_text#{memoDate}"
            bot.editMessageText(msgIdent, f"💡 <b>Data memo: {memoDate}</b>\n"
                                          f"Inviami il testo del memo, o premi /annulla per annullare.",
                                parse_mode="HTML", reply_markup=None)

    else:
        bot.sendMessage(chatId, "ℹ️ <b>Bot in manutenzione</b>\n"
                                "Il bot è attualmente in manutenzione per problemi con ClasseViva, e tutte le sue "
                                "funzioni sono temporaneamente disabilitate.\n"
                                "Non eliminare questa chat: se vuoi puoi archiviarla su Telegram, così appena "
                                "ci saranno notizie arriverà un messaggio qui.\n\n"
                                "/moreinfo", parse_mode="HTML")


def accept_message(msg):
    Thread(target=reply, name=f"msg_{msg['chat']['id']}", args=[msg]).start()

def accept_button(msg):
    Thread(target=button_press, name=f"btn_{msg['from']['id']}", args=[msg]).start()

bot.message_loop(
    callback={'chat': accept_message, 'callback_query': accept_button}
)

while True:
    sleep(60)
    now = datetime.now()
    doLongFetch = now.strftime("%H:%M") == js_settings["fullUpdatesTime"]
    if now.minute % updatesEvery == 0:
        helpers.renewProxy()
        runDailyUpdates(now)
        runUpdates(long_fetch=doLongFetch)
