from time import sleep
from pony.orm import db_session
from modules.database import Data, ParsedData
from modules.crypter import decrypt_password
from modules.api import AuthenticationFailedError, ApiServerError
from telepot.exception import TelegramError, BotWasBlockedError
import modules.parser as resp


maxMessageLength = 4096
adminIds = [368894926] # Bot Creator


def sendLongMessage(bot, chatId, text: str, **kwargs):
    if len(text) <= maxMessageLength:
        return bot.sendMessage(chatId, text, **kwargs)

    parts = []
    while len(text) > 0:
        if len(text) > maxMessageLength:
            part = text[:maxMessageLength]
            first_lnbr = part.rfind('\n')
            if first_lnbr != -1:
                parts.append(part[:first_lnbr])
                text = text[(first_lnbr + 1):]
            else:
                parts.append(part)
                text = text[maxMessageLength:]
        else:
            parts.append(text)
            break

    msg = None
    for part in parts:
        msg = bot.sendMessage(chatId, part, **kwargs)
        sleep(0.5)
    return msg


def isAdmin(chatId: None):
    if not chatId:
        return adminIds
    return chatId in adminIds


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
    userdata.comunicazioni = {}

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
    stored.comunicazioni = ""


def userLogin(bot, user, api_type):
    if not isUserLogged(user):
        return False
    try:
        api_type.login(user.username, decrypt_password(user))
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


def userLogout(api_type):
    api_type.logout()


@db_session
def fetchAndStore(user, api_type, fetch_long=False):
    newDidattica = api_type.didattica()
    newNote = api_type.note()
    newVoti = api_type.voti()
    newAgenda = api_type.agenda(14)
    newAssenze = api_type.assenze()
    newLezioni = api_type.lezioni()
    newComunicazioni = api_type.comunicazioni()

    stored = ParsedData.get(chatId=user.chatId)
    stored.note = resp.parseNote(newNote)
    stored.voti = resp.parseVoti(newVoti, user)
    stored.assenze = resp.parseAssenze(newAssenze)
    stored.agenda = resp.parseAgenda(newAgenda)
    stored.domani = resp.parseDomani(newAgenda)
    stored.lezioni = resp.parseLezioni(newLezioni)
    stored.didattica = resp.parseDidattica(newDidattica)
    stored.comunicazioni = resp.parseComunicazioni(newComunicazioni)

    if fetch_long:
        newInfo = api_type.info()
        newProf = api_type.materie()
        stored.info = resp.parseInfo(newInfo)
        stored.prof = resp.parseMaterie(newProf)

    userLogout(api_type)
    return newDidattica, newNote, newVoti, newAgenda, newComunicazioni


@db_session
def updateUserdata(user, newDidattica, newNote, newVoti, newAgenda, newComunicazioni):
    userdata = Data.get(chatId=user.chatId)
    userdata.didattica = newDidattica
    userdata.note = newNote
    userdata.voti = newVoti
    userdata.agenda = newAgenda
    userdata.comunicazioni = newComunicazioni
