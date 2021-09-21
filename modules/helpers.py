from time import sleep
from telepotpro import Bot
from telepotpro.exception import TelegramError, BotWasBlockedError
from json import load as jsload
from os.path import abspath, dirname, join
from stem import Signal
from stem.control import Controller

from modules import parsers
from modules.crypter import decrypt_password
from modules.database import User, Data, ParsedData

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
    user.delete()

    userdata = Data.get(chatId=chatId)
    userdata.delete()

    stored = ParsedData.get(chatId=chatId)
    stored.delete()


def userLogin(chatId, _api, _quiet=False):
    from modules.api import AuthenticationFailedError, ApiServerError

    user = User.get(chatId=chatId)
    if not hasStoredCredentials(chatId):
        return False
    try:
        _api.login(user.username, decrypt_password(chatId))
        return True
    except AuthenticationFailedError:
        if not _quiet:
            clearUserData(chatId)
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


def fetchStrict(_api):
    data = {
        'didattica': _api.didattica(),
        'note': _api.note(),
        'voti': _api.voti(),
        'agenda': _api.agenda(),
        'circolari': _api.circolari()
    }
    return data


def fetchAndStore(chatId, _api, data, fetch_long=False):
    if not data: data = fetchStrict(_api)
    stored = ParsedData.get(chatId=chatId)

    newAssenze = _api.assenze()
    newLezioni = _api.lezioni()
    if fetch_long:
        newInfo = _api.info()
        newProf = _api.materie()
        stored.info = parsers.parseInfo(newInfo)
        stored.prof = parsers.parseMaterie(newProf)

    stored.note = parsers.parseNote(data['note'])
    stored.voti = parsers.parseVoti(data['voti'], chatId)
    stored.assenze = parsers.parseAssenze(newAssenze)
    stored.agenda = parsers.parseAgenda(data['agenda'])
    stored.domani = parsers.parseDomani(data['agenda'])
    stored.lezioni = parsers.parseLezioni(newLezioni)
    stored.didattica = parsers.parseDidattica(data['didattica'])
    stored.circolari = parsers.parseCircolari(data['circolari'])


def updateUserdata(chatId, data):
    userdata = Data.get(chatId=chatId)
    if data['didattica']: userdata.didattica = data['didattica']
    if data['note']: userdata.note = data['note']
    if data['voti']: userdata.voti = data['voti']
    if data['agenda']: userdata.agenda = data['agenda']
    if data['circolari']: userdata.circolari = data['circolari']
