from pony.orm import Database, Required, Optional, Json

db = Database("sqlite", "../classevivabot.db", create_db=True)


class User(db.Entity):
    chatId = Required(int)
    username = Optional(str)
    password = Optional(str)
    status = Required(str, default="normal")


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


class Settings(db.Entity):
    chatId = Required(int)
    wantsNotifications = Required(bool, default=True)
    doNotDisturb = Required(bool, default=True)
    wantsDailyUpdates = Required(bool, default=True)
    dailyUpdatesHour = Required(str, default="13:30")


db.generate_mapping(create_tables=True)