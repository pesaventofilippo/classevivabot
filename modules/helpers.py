from time import sleep
from telepotpro import Bot
from modules.database import User, Data, ParsedData
from modules.crypter import decrypt_password
from telepotpro.exception import TelegramError, BotWasBlockedError
from modules import parsers
from json import load as jsload
from os.path import abspath, dirname, join
from stem import Signal
from stem.control import Controller

with open(join(dirname(abspath(__file__)), "../settings.json")) as settings_file:
    js_settings = jsload(settings_file)

maxMessageLength = 4096
adminIds = js_settings["admins"]
bot = Bot(js_settings["token"])


def renewProxy():
    if js_settings["useProxy"]:
        with Controller.from_port(address=js_settings["torProxyIP"], port=js_settings["torControlPort"]) as controller:
            controller.authenticate(password=js_settings["torControlPassword"])
            controller.signal(Signal.NEWNYM)


def getProxy():
    if js_settings["useProxy"]:
        proxyIP = "socks5://{}:{}".format(js_settings["torProxyIP"], js_settings["torProxyPort"])
    else:
        proxyIP = ""
    return {
        "http": proxyIP,
        "https": proxyIP
    }


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


def hasStoredCredentials(chatId):
    user = User.get(chatId=chatId)
    return (user.username != "") and (user.password != "")


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


def userLogin(chatId, api_type, _quiet=False):
    from modules.api import AuthenticationFailedError, ApiServerError
    user = User.get(chatId=chatId)
    if not hasStoredCredentials(chatId):
        return False
    try:
        api_type.login(user.username, decrypt_password(chatId))
        return True
    except AuthenticationFailedError:
        clearUserData(chatId)
        if not _quiet:
            try:
                bot.sendMessage(chatId, "😯 Le tue credenziali di accesso sono errate.\n"
                                        "Effettua nuovamente il /login per favore.")
            except (TelegramError, BotWasBlockedError):
                pass
        return False
    except ApiServerError:
        if not _quiet:
            try:
                bot.sendMessage(chatId, "⚠️ I server di ClasseViva non sono raggiungibili.\n"
                                        "Riprova tra qualche minuto.")
            except (TelegramError, BotWasBlockedError):
                pass
        return False


def fetchStrict(api_type):
    data = {
        'didattica': api_type.didattica(),
        'note': api_type.note(),
        'voti': api_type.voti(),
        'agenda': api_type.agenda(14),
        'circolari': api_type.circolari()
    }
    return data


def fetchAndStore(chatId, api_type, data, fetch_long=False):
    newAssenze = api_type.assenze()
    newLezioni = api_type.lezioni()
    if fetch_long:
        newInfo = api_type.info()
        newProf = api_type.materie()

    stored = ParsedData.get(chatId=chatId)
    stored.note = parsers.parseNote(data['note'])
    stored.voti = parsers.parseVoti(data['voti'], chatId)
    stored.assenze = parsers.parseAssenze(newAssenze)
    stored.agenda = parsers.parseAgenda(data['agenda'])
    stored.domani = parsers.parseDomani(data['agenda'])
    stored.lezioni = parsers.parseLezioni(newLezioni)
    stored.didattica = parsers.parseDidattica(data['didattica'])
    stored.circolari = parsers.parseCircolari(data['circolari'])
    if fetch_long:
        stored.info = parsers.parseInfo(newInfo)
        stored.prof = parsers.parseMaterie(newProf)


def updateUserdata(chatId, data):
    userdata = Data.get(chatId=chatId)
    if data['didattica']: userdata.didattica = data['didattica']
    if data['note']: userdata.note = data['note']
    if data['voti']: userdata.voti = data['voti']
    if data['agenda']: userdata.agenda = data['agenda']
    if data['circolari']: userdata.circolari = data['circolari']
