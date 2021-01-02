from pony.orm import Database, Required, Optional, Json, StrArray

db = Database("sqlite", "../classevivabot.db", create_db=True)


class User(db.Entity):
    chatId = Required(int)
    username = Optional(str)
    password = Optional(str)
    status = Required(str, default="normal")
    lastPeriod = Required(int, default=1)
    remainingCalls = Required(int, default=3)


class Data(db.Entity):
    chatId = Required(int)
    didattica = Optional(Json)
    info = Optional(Json)
    prof = Optional(Json)
    note = Optional(Json)
    voti = Optional(Json)
    assenze = Optional(Json)
    agenda = Optional(Json)
    domani = Optional(Json)
    lezioni = Optional(Json)
    circolari = Optional(Json)


class ParsedData(db.Entity):
    chatId = Required(int)
    didattica = Optional(str)
    info = Optional(str)
    prof = Optional(str)
    note = Optional(str)
    voti = Optional(str)
    assenze = Optional(str)
    agenda = Optional(str)
    domani = Optional(str)
    lezioni = Optional(str)
    circolari = Optional(str)


class Settings(db.Entity):
    chatId = Required(int)
    wantsNotifications = Required(bool, default=True)
    doNotDisturb = Required(bool, default=True)
    wantsDailyUpdates = Required(bool, default=True)
    dailyUpdatesHour = Required(str, default="13:30")
    activeNews = Required(StrArray, default=["didattica", "note", "voti", "agenda", "circolari"])


class Circolari(db.Entity):
    name = Required(str)
    pubId = Required(int)
    eventCode = Required(str)
    attachName = Required(str)


class File(db.Entity):
    name = Required(str)
    fileId = Required(int)


db.generate_mapping(create_tables=True)


if __name__ == "__main__":
    from sys import argv

    if "--create-tables" in argv:
        print("Creating orphan tables...")
        from pony.orm import db_session, select
        with db_session:
            for chatId in select(u.chatId for u in User)[:]:
                if not Data.exists(lambda d: d.chatId == chatId):
                    Data(chatId=chatId)
                if not ParsedData.exists(lambda p: p.chatId == chatId):
                    ParsedData(chatId=chatId)
                if not Settings.exists(lambda s: s.chatId == chatId):
                    Settings(chatId=chatId)
        print("Creating tables done.")
