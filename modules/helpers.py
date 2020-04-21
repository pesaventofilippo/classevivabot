from time import sleep
from telepot import Bot
from modules.database import User, Data, ParsedData
from modules.crypter import decrypt_password
from telepot.exception import TelegramError, BotWasBlockedError
from modules import parser
from requests import get

maxMessageLength = 4096
adminIds = [368894926] # Bot Creator
bot = None
selectedProxy = {
    "http":  "",
    "https": ""
}


def setBot(token):
    global bot
    bot = Bot(token)


def renewProxy():
    global selectedProxy
    res = get("https://api.getproxylist.com/proxy"
              "?lastTested=3600"
              "&allowsUserAgentHeader=1"
              "&allowsCustomHeaders=1"
              "&allowsPost=1"
              "&allowsHttps=1"
              "&country[]=US&country[]=IT&country[]=DE&country[]=CH")
    if res.status_code == 200:
        proxy = res.json()
        selectedProxy["http"] =  "{}:{}".format(proxy['ip'], proxy['port'])
        selectedProxy["https"] = "{}:{}".format(proxy['ip'], proxy['port'])


def getProxy():
    if not selectedProxy.get("http"):
        renewProxy()
    return selectedProxy


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
    stored.note = parser.parseNote(data['note'])
    stored.voti = parser.parseVoti(data['voti'], chatId)
    stored.assenze = parser.parseAssenze(newAssenze)
    stored.agenda = parser.parseAgenda(data['agenda'])
    stored.domani = parser.parseDomani(data['agenda'])
    stored.lezioni = parser.parseLezioni(newLezioni)
    stored.didattica = parser.parseDidattica(data['didattica'])
    stored.circolari = parser.parseCircolari(data['circolari'])
    if fetch_long:
        stored.info = parser.parseInfo(newInfo)
        stored.prof = parser.parseMaterie(newProf)


def updateUserdata(chatId, data):
    userdata = Data.get(chatId=chatId)
    userdata.didattica = data['didattica']
    userdata.note = data['note']
    userdata.voti = data['voti']
    userdata.agenda = data['agenda']
    userdata.circolari = data['circolari']
