from modules.database import User, Document
from pony.orm import select
from datetime import date, timedelta, datetime

TAB = " " * 4


def sanitize(dinput):
    if not dinput:
        return None
    from xml.sax.saxutils import escape
    esc_table = {
        ">": "&gt;",
        "<": "&lt;"
    }
    return escape(dinput, esc_table)


def innerParseNotes(event):
    evtauthor = event['authorName'].title()
    evttime = date.fromisoformat(event['evtDate']).strftime("%d/%m/%Y")
    evttext = event['evtText'] if event['readStatus'] else "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione \"annotazioni\" per leggere questa nota."
    return evtauthor, evttime, sanitize(evttext)


def innerParseFolders(folder):
    folderName = "Altro" if folder['folderName'] == "Uncategorized" else sanitize(folder['folderName'])
    return f"\n{TAB}📂 <b>{folderName}</b>"


def innerParseFiles(file):
    fileName = "Senza nome" if file['contentName'] == "" else sanitize(file['contentName'])
    fileId = file['contentId']
    fileType = file['objectType']
    fileIcon = "📎" if fileType == "link" else "📝"
    return f"\n{TAB*2}{fileIcon} <a href=\"https://t.me/ClasseVivaIT_Bot?start={fileType}{fileId}\">{fileName}</a>"


def parseDidattica(data):
    if (data is None) or (not data.get('didacticts')):
        return "\n\n📌 Nessun file caricato."

    result = ""
    firstProf = True
    for prof in data['didacticts']:
        string = f"\n\n👤 <b>{prof['teacherName']}</b>"
        result += string if firstProf else "\n" + string
        firstProf = False

        firstFolder = True
        for folder in prof['folders']:
            string = innerParseFolders(folder)
            result += string if firstFolder else "\n" + string
            firstFolder = False

            for upfile in folder['contents']:
                result += innerParseFiles(upfile)

    return result


def parseInfo(data):
    if (data is None) or (not data.get('cards')):
        return "📌 Nessuna info disponibile."

    info = data['cards'][0]
    bday = date.fromisoformat(info['birthDate']).strftime("%d/%m/%Y")
    userType = "Studente" if info['usrType'] == "S" \
        else "Genitore" if info['usrType'] == "G" \
        else info['usrType']

    return f"👤 Nome: <b>{info['firstName']}</b>\n" \
           f"👤 Cognome: <b>{info['lastName']}</b>\n" \
           f"📅 Nascita: <b>{bday}</b>\n" \
           f"💳 Codice Fiscale: <b>{info['fiscalCode']}</b>\n" \
           f"👤 Username: <b>{info['ident']}</b>\n" \
           f"\n" \
           f"🏫 Nome Scuola: <b>{info['schDedication']}</b>\n" \
           f"🏫 Tipo Scuola: <b>{info['schName']}</b>\n" \
           f"🏫 ID Scuola: <b>{info['schCode']}</b>\n" \
           f"🏫 ID MIUR Scuola: <b>{info['miurSchoolCode']}</b>\n" \
           f"🏛 Città: <b>{info['schCity']}</b>\n" \
           f"📍 Provincia: <b>{info['schProv']}</b>\n" \
           f"\n" \
           f"👤 UserID: <b>{info['usrId']}</b>\n" \
           f"👤 Tipo Utente: <b>{userType}</b>"


def parseMaterie(data):
    if (data is None) or (not data.get('subjects')):
        return "\n\n📌 Nessun prof attualmente registrato."

    result = ""
    firstMateria = True
    for materia in data['subjects']:
        string = f"\n\n📚 <b>{materia['description']}</b>"
        result += "\n" + string if firstMateria else string
        firstMateria = False
        for prof in materia['teachers']:
            result += f"\n{TAB}👤 {prof['teacherName']}"
    return result


def parseNote(data):
    if (data is None) or (not data.get('NTCL') and not data.get('NTWN') and not data.get('NTTE')):
        return "\n\n✅ Nessuna annotazione rilevata!"

    result = ""
    for nota in data['NTCL']:
        author, time, text = innerParseNotes(nota)
        result += f"\n\n🚫 <b>Nota disciplinare</b> di <b>{author}</b> del {time}:\n{text}"

    for avviso in data['NTWN']:
        author, time, text = innerParseNotes(avviso)
        result += f"\n\n⚠️ <b>Richiamo ({avviso['warningType'].lower()})</b> di <b>{author}</b> del {time}:\n{text}"

    for annotazione in data['NTTE']:
        author, time, text = innerParseNotes(annotazione)
        result += f"\n\nℹ️ <b>Annotazione</b> di <b>{author}</b> del {time}:\n{text}"

    return result


def parseVoti(data, chatId):
    if (data is None) or (not data.get('grades')):
        return "\n📕 Non hai ancora nessun voto!"

    user = User.get(chatId=chatId)
    votiOrdinati = {}
    media = {}
    periods = []
    for voto in data['grades']:
        period = voto['periodPos']
        periods.append(period)
        if period >= user.lastPeriod:
            materia = voto['subjectDesc']
            value = "Voto " + voto['displayValue']
            tipo = f"• {sanitize(voto['componentDesc'])} " if voto['componentDesc'] else ""
            time = date.fromisoformat(voto['evtDate']).strftime("%d/%m/%Y")
            desc = f"\n<i>{sanitize(voto['notesForFamily'])}</i>" if voto['notesForFamily'] else ""
            colore = "📗" if voto['color'] == "green" else "📕" if voto['color'] == "red" else "📘"

            str_voto = f"\n\n{colore} <b>{value}</b> {tipo}• {time} {desc}"
            if materia not in votiOrdinati:
                votiOrdinati[materia] = []
            if materia not in media:
                media[materia] = []
            votiOrdinati[materia].append(str_voto)

            if "total" not in media:
                media["total"] = []

            if colore != "📘":
                votoRaw = value[5:]
                values = {
                    "½": +0.50,
                    "+": +0.25,
                    "-": -0.25
                }

                if votoRaw[-1] in values.keys():
                    votoValue = float(votoRaw[:-1]) + values[votoRaw[-1]]
                    media[materia].append(votoValue)
                    media["total"].append(votoValue)
                else:
                    try:
                        votoValue = float(votoRaw)
                        media[materia].append(votoValue)
                        media["total"].append(votoValue)
                    except ValueError:
                        pass

    if periods:
        user.lastPeriod = max(periods)

    firstMateria = True
    materie = {}
    for materia, voti in votiOrdinati.items():
        if materia not in materie:
            materie[materia] = ""
        for voto in voti:
            materie[materia] += voto
        if len(media[materia]) == 0:
            media[materia] = False
        else:
            media[materia] = round(sum(media[materia]) / len(media[materia]), 2)

        if media[materia]:
            string = f"\n\n📚 <b>{materia}\n" \
                     f"{TAB}Media: {media[materia]}</b>{materie[materia]}"
            materie[materia] = string if firstMateria else "\n\n" + string
            firstMateria = False
        else:
            string = f"\n\n📚 <b>{materia}</b>{materie[materia]}"
            materie[materia] = string if firstMateria else "\n\n" + string
            firstMateria = False

    if "total" not in media:
        media["total"] = False
    elif len(media["total"]) == 0:
        media["total"] = False
    else:
        media["total"] = round(sum(media["total"]) / len(media["total"]), 2)
    
    result = ""
    for materia in materie:
        result += materie[materia]
    
    if media["total"]:
        result += f"\n\n📚 <b>Media totale: {media['total']}</b>"
        result += f"\n🕙 <i>Quadrimestre: {user.lastPeriod}</i>"

    return result


def parseAssenze(data):
    if (data is None) or (not data.get('events')):
        return "\n\n✅ Nessuna assenza/ritardo rilevati!"

    assenze = ""
    ritardi = ""
    ritardiBrevi = ""
    usciteAnticipate = ""

    for evento in data['events']:
        desc = "Non specificato" if not evento['justifReasonDesc'] else sanitize(evento['justifReasonDesc'].lower())
        toJustify = "\n ⚠️ Da giustificare!" if not evento['isJustified'] else ""
        time = date.fromisoformat(evento['evtDate']).strftime("%d/%m/%Y")
        evtString = f"\n - {time}: {desc}{toJustify}"

        if evento['evtCode'] == "ABA0":
            if not assenze:
                assenze = "\n\n\n❌ <b>Assenze</b>:"
            assenze += evtString

        elif evento['evtCode'] == "ABR0":
            if not ritardi:
                ritardi = "\n\n\n🏃 <b>Ritardi</b>:"
            ritardi += evtString

        elif evento['evtCode'] == "ABR1":
            if not ritardiBrevi:
                ritardiBrevi = "\n\n\n🚶 <b>Ritardi Brevi</b>:"
            ritardiBrevi += evtString

        elif evento['evtCode'] == "ABU0":
            if not usciteAnticipate:
                usciteAnticipate = "\n\n\n🚪 <b>Uscite Anticipate</b>:"
            usciteAnticipate += evtString

    return assenze + ritardi + ritardiBrevi + usciteAnticipate


def parseAgenda(data, chatId):
    memos = select(m for m in Document if m.chatId == chatId and m.type == "memo")[:]
    if ((data is None) or (not data.get('agenda'))) and memos is None:
        return "\n🗓 L'agenda è ancora vuota."

    result = ""
    separator = "\n"
    eventslist = data['agenda']
    eventslist.sort(key=lambda x: str(x['evtDatetimeBegin']).split("T", 1)[0])
    today = date.today()
    for event in eventslist:
        date_raw = str(event['evtDatetimeBegin']).split("T")[0]
        evtTime = date.fromisoformat(date_raw)

        if evtTime > today:
            evtType = "📌" if event['evtCode'] == "AGNT" else "📝"
            result += f"{separator}{evtType} {evtTime.strftime('%d/%m/%Y')} • <b>{event['authorName'].title()}</b>\n{sanitize(event['notes'])}"
            separator = "\n\n\n"

    for memo in memos:
        evtTime = datetime.strptime(memo.data["date"], "%d/%m/%Y").date()
        if evtTime > today:
            result += f"{separator}💡 {memo.data['date']} • <b>Memo</b>\n{sanitize(memo.data['text'])}"
            separator = "\n\n\n"

    return result


def parseDomani(data, chatId):
    memos = select(m for m in Document if m.chatId == chatId and m.type == "memo")[:]
    if ((data is None) or (not data.get('agenda'))) and memos is None:
        return "\n🗓 Non hai compiti per domani."

    result = ""
    separator = "\n"
    today = date.today()
    toCheck = today + timedelta(days=(1 if today.isoweekday() != 6 else 2))
    for event in data['agenda']:
        date_raw = str(event['evtDatetimeBegin']).split("T")[0]
        evtTime = date.fromisoformat(date_raw)

        if evtTime == toCheck:
            evtType = "📌" if event['evtCode'] == "AGNT" else "📝"
            result += f"{separator}{evtType} <b>{event['authorName'].title()}</b>\n{sanitize(event['notes'])}"
            separator = "\n\n\n"

    for memo in memos:
        evtTime = datetime.strptime(memo.data["date"], "%d/%m/%Y").date()

        if evtTime == toCheck:
            result += f"{separator}💡 <b>Memo</b>\n{sanitize(memo.data['text'])}"
            separator = "\n\n\n"

    return "\n🗓 Non hai compiti per domani." if result == "" else result


def parseLezioni(data):
    if (data is None) or (not data.get('lessons')):
        return "🎈 Nessuna lezione, per oggi."

    result = ""
    lessonsList = data['lessons']
    lessonsList.sort(key=lambda x: str(x['evtHPos']))
    for lezione in lessonsList:
        ora = lezione['evtHPos']
        desc = f"\n{sanitize(lezione['lessonArg'])}" if lezione['lessonArg'] else ""
        tipo = lezione['lessonType']
        materia = lezione['subjectDesc']
        result += f"✏️ {ora}° ora • <b>{tipo}</b> di <b>{materia}</b>{desc}\n\n"
    return result


def parseCircolari(data):
    if (data is None) or (not data.get('items')):
        return "\n\n📩 Non ci sono circolari da leggere."

    result = ""
    for item in data['items']:
        status = item['cntStatus']
        title = sanitize(item['cntTitle'])
        isRead = item['readStatus']
        if len(item['attachments']) > 0:
            pubId = item['pubId']
            evCode = item['evtCode']

            if (status == 'active') and not isRead:
                result += f"\n\n✉️ <a href=\"https://t.me/ClasseVivaIT_Bot?start=circ{evCode}-{pubId}\">{title}</a>"
        else:
            if (status == 'active') and not isRead:
                result += f"\n\n✉️ {title}"

    return result if result else "\n\n📩 Non ci sono circolari da leggere."



def parseNewDidattica(oldData, newData):
    if (newData is None) or (not newData.get('didacticts')):
        return None
    if (oldData is None) or (not oldData.get('didacticts')):
        return parseDidattica(newData)

    result = ""
    firstProf = True
    for prof in newData['didacticts']:
        oldProfs = oldData['didacticts']
        oldProfIds = [i['teacherId'] for i in oldProfs]
        if prof['teacherId'] not in oldProfIds:
            string = f"\n\n👤 <b>{prof['teacherName']}</b>"
            result += string if firstProf else "\n" + string
            firstProf = False

            firstFolder = True
            for folder in prof['folders']:
                string = innerParseFolders(folder)
                result += string if firstFolder else "\n" + string
                firstFolder = False

                for upfile in folder['contents']:
                    result += innerParseFiles(upfile)

        else:
            firstFolder = True
            for folder in prof['folders']:
                oldProfFolders = [i['folders'] for i in oldProfs if i['teacherId'] == prof['teacherId']][0]
                oldProfFolderIds = [i['folderId'] for i in oldProfFolders]
                if folder['folderId'] not in oldProfFolderIds:
                    if firstFolder:
                        string = f"\n\n👤 <b>{prof['teacherName']}</b>"
                        result += string if firstProf else "\n" + string
                        firstProf = False
                    string = innerParseFolders(folder)
                    result += string if firstFolder else "\n" + string
                    firstFolder = False

                    for upfile in folder['contents']:
                        result += innerParseFiles(upfile)

                else:
                    firstFile = True
                    for upfile in folder['contents']:
                        oldFolderFiles = [i['contents'] for i in oldProfFolders if i['folderId'] == folder['folderId']][0]
                        oldFolderFileIds = [i['contentId'] for i in oldFolderFiles]
                        if upfile['contentId'] not in oldFolderFileIds:
                            if firstFile:
                                string = innerParseFolders(folder)
                                result += string if firstFolder else "\n" + string
                                firstFolder = False
                            result += innerParseFiles(upfile)
                            firstFile = False

    return result if result != "" else None


def parseNewNote(oldData, newData):
    if (newData is None) or (not newData.get('NTCL') and not newData.get('NTWN') and not newData.get('NTTE')):
        return None
    if (oldData is None) or (not oldData.get('NTCL') and not oldData.get('NTWN') and not oldData.get('NTTE')):
        return parseNote(newData)

    result = ""
    for nota in newData['NTCL']:
        if (not oldData.get('NTCL')) or (nota not in oldData['NTCL']):
            author, time, text = innerParseNotes(nota)
            result += f"\n\n🚫 <b>Nota disciplinare</b> di <b>{author}</b> del {time}:\n{text}"

    for avviso in newData['NTWN']:
        if (not oldData.get('NTWN')) or (avviso not in oldData['NTWN']):
            author, time, text = innerParseNotes(avviso)
            result += f"\n\n⚠️ <b>Richiamo ({avviso['warningType'].lower()})</b> di <b>{author}</b> del {time}:\n{text}"

    for annotazione in newData['NTTE']:
        if (not oldData.get('NTTE')) or (annotazione not in oldData['NTTE']):
            author, time, text = innerParseNotes(annotazione)
            result += f"\n\nℹ️ <b>Annotazione</b> di <b>{author}</b> del {time}:\n{text}"

    return result if result != "" else None


def parseNewVoti(oldData, newData, chatId):
    if (newData is None) or (not newData.get('grades')):
        return None
    if (oldData is None) or (not oldData.get('grades')):
        return parseVoti(newData, chatId)

    votiOrdinati = {}
    periods = []
    for voto in newData['grades']:
        if voto not in oldData['grades']:
            period = voto['periodPos']
            periods.append(period)
            materia = voto['subjectDesc']
            value = "Voto " + voto['displayValue']
            tipo = f"• {sanitize(voto['componentDesc'])} " if voto['componentDesc'] else ""

            time = date.fromisoformat(voto['evtDate']).strftime("%d/%m/%Y")
            desc = f"\n<i>{sanitize(voto['notesForFamily'])}</i>" if voto['notesForFamily'] else ""
            colore = "📗" if voto['color'] == "green" else "📕" if voto['color'] == "red" else "📘"
            str_voto = f"\n\n{colore} <b>{value}</b> {tipo}• {time} {desc}"
            if materia not in votiOrdinati:
                votiOrdinati[materia] = []
            votiOrdinati[materia].append(str_voto)
    if periods:
        user = User.get(chatId=chatId)
        user.lastPeriod = max(periods)

    result = ""
    firstMateria = True
    for materia, voti in votiOrdinati.items():
        string = f"\n\n📚 <b>{materia}</b>"
        result += string if firstMateria else "\n\n" + string
        firstMateria = False
        for voto in voti:
            result += voto

    return result if result != "" else None


def parseNewAgenda(oldData, newData, chatId):
    if (newData is None) or (not newData.get('agenda')):
        return None
    if (oldData is None) or (not oldData.get('agenda')):
        return parseAgenda(newData, chatId)

    result = ""
    firstEvent = True
    for event in newData['agenda']:
        if event not in oldData['agenda']:
            date_raw = str(event['evtDatetimeBegin']).split("T")[0]
            evtTime = date.fromisoformat(date_raw).strftime("%d/%m/%Y")
            evtType = "📌" if event['evtCode'] == "AGNT" else "📝"
            separator = "\n" if firstEvent else "\n\n\n"
            firstEvent = False
            result += f"{separator}{evtType} {evtTime} • <b>{event['authorName'].title()}</b>\n{sanitize(event['notes'])}"

    return result if result != "" else None


def parseNewCircolari(oldData, newData):
    if (newData is None) or (not newData.get('items')):
        return None
    if (oldData is None) or (not oldData.get('items')):
        return parseCircolari(newData)

    result = ""
    isFirst = True
    for item in newData['items']:
        if item not in oldData['items']:
            status = item['cntStatus']
            title = sanitize(item['cntTitle'])
            isRead = item['readStatus']
            if len(item['attachments']) > 0:
                pubId = item['pubId']
                evCode = item['evtCode']

                if (status == 'active') and not isRead:
                    string = f"\n✉️ <a href=\"https://t.me/ClasseVivaIT_Bot?start=circ{evCode}-{pubId}\">{title}</a>"
                    result += string if isFirst else "\n" + string
                    isFirst = False
            else:
                if (status == 'active') and not isRead:
                    string = f"\n✉️ {title}"
                    result += string if isFirst else "\n" + string
                    isFirst = False

    return result if result != "" else None
