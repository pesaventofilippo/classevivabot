from time import sleep
from pony.orm import db_session
from telepot import Bot
from modules.database import User, Data, ParsedData
from modules.crypter import decrypt_password
from modules.api import AuthenticationFailedError, ApiServerError
from telepot.exception import TelegramError, BotWasBlockedError
from modules import parser

maxMessageLength = 4096
adminIds = [368894926] # Bot Creator
bot = None


def setBot(token):
    global bot
    bot = Bot(token)


def sendLongMessage(chatId, text: str, **kwargs):
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


def isAdmin(chatId=None):
    if not chatId:
        return adminIds
    return chatId in adminIds


@db_session
def hasStoredCredentials(chatId):
    user = User.get(chatId=chatId)
    return (user.username != "") and (user.password != "")


@db_session
def clearUserData(chatId):
    user = User.get(chatId=chatId)
    user.username = ""
    user.password = ""
    user.status = "normal"
    user.lastPeriod = 1

    userdata = Data.get(chatId=chatId)
    userdata.didattica = {}
    userdata.info = {}
    userdata.prof = {}
    userdata.note = {}
    userdata.voti = {}
    userdata.assenze = {}
    userdata.agenda = {}
    userdata.domani = {}
    userdata.lezioni = {}
    userdata.circolari = {}

    stored = ParsedData.get(chatId=chatId)
    stored.didattica = ""
    stored.info = ""
    stored.prof = ""
    stored.note = ""
    stored.voti = ""
    stored.assenze = ""
    stored.agenda = ""
    stored.domani = ""
    stored.lezioni = ""
    stored.circolari = ""


@db_session
def userLogin(chatId, api_type, _apiLock=None, _quiet=False):
    user = User.get(chatId=chatId)
    if not hasStoredCredentials(chatId):
        if _apiLock:
            _apiLock.release()
        return False
    try:
        api_type.login(user.username, decrypt_password(chatId))
        return True
    except AuthenticationFailedError:
        if _apiLock:
            _apiLock.release()
        clearUserData(chatId)
        if not _quiet:
            try:
                bot.sendMessage(chatId, "😯 Le tue credenziali di accesso sono errate.\n"
                                                "Effettua nuovamente il /login per favore.")
            except (TelegramError, BotWasBlockedError):
                pass
        return False
    except ApiServerError:
        if _apiLock:
            _apiLock.release()
        if not _quiet:
            try:
                bot.sendMessage(chatId, "⚠️ I server di ClasseViva non sono raggiungibili.\n"
                                                "Riprova tra qualche minuto.")
            except (TelegramError, BotWasBlockedError):
                pass
        return False


def userLogout(api_type):
    api_type.logout()


@db_session
def fetchAndStore(chatId, api_type, _apiLock, fetch_long=False):
    newDidattica = api_type.didattica()
    newNote = api_type.note()
    newVoti = api_type.voti()
    newAgenda = api_type.agenda(14)
    newAssenze = api_type.assenze()
    newLezioni = api_type.lezioni()
    newCircolari = api_type.circolari()
    if fetch_long:
        newInfo = api_type.info()
        newProf = api_type.materie()
    userLogout(api_type)    
    _apiLock.release()
    
    stored = ParsedData.get(chatId=chatId)
    stored.note = parser.parseNote(newNote)
    stored.voti = parser.parseVoti(newVoti, chatId)
    stored.assenze = parser.parseAssenze(newAssenze)
    stored.agenda = parser.parseAgenda(newAgenda)
    stored.domani = parser.parseDomani(newAgenda)
    stored.lezioni = parser.parseLezioni(newLezioni)
    stored.didattica = parser.parseDidattica(newDidattica)
    stored.circolari = parser.parseCircolari(newCircolari)
    if fetch_long:
        stored.info = parser.parseInfo(newInfo)
        stored.prof = parser.parseMaterie(newProf)

    return newDidattica, newNote, newVoti, newAgenda, newCircolari


@db_session
def updateUserdata(chatId, newDidattica, newNote, newVoti, newAgenda, newCircolari):
    userdata = Data.get(chatId=chatId)
    userdata.didattica = newDidattica
    userdata.note = newNote
    userdata.voti = newVoti
    userdata.agenda = newAgenda
    userdata.circolari = newCircolari
