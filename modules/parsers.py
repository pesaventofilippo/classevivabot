from modules.database import User


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
    evttime = event['evtDate'].lower().split("-", 2)
    evttext = event['evtText'] if event['readStatus'] else "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione \"annotazioni\" per leggere questa nota."
    return evtauthor, evttime, sanitize(evttext)


def parseDidattica(data):
    if (data is None) or (not data.get('didacticts')):
        return "\n\n📌 Nessun file caricato."

    result = ""
    firstProf = True
    for prof in data['didacticts']:
        string = "\n\n👤 <b>{0}</b>".format(prof['teacherName'])
        result += string if firstProf else "\n" + string
        firstProf = False

        firstFolder = True
        for folder in prof['folders']:
            folderName = "Altro" if folder['folderName'] == "Uncategorized" else sanitize(folder['folderName'])
            string = "\n    📂 <b>{0}</b>".format(folderName)
            result += string if firstFolder else "\n" + string
            firstFolder = False

            for upfile in folder['contents']:
                fileName = "Senza nome" if upfile['contentName'] == "" else sanitize(upfile['contentName'])
                fileId = upfile['contentId']
                result += "\n        📝 <a href=\"https://t.me/ClasseVivaIT_Bot?start=file{}\">{}</a>".format(fileId, fileName)

    return result


def parseInfo(data):
    if (data is None) or (not data.get('cards')):
        return "📌 Nessuna info disponibile."

    info = data['cards'][0]
    bday = info['birthDate'].lower().split("-", 2)
    userType = "Studente" if info['usrType'] == "S" \
        else "Genitore" if info['usrType'] == "G" \
        else info['usrType']

    return f"👤 Nome: <b>{info['firstName']}</b>\n" \
           f"👤 Cognome: <b>{info['lastName']}</b>\n" \
           f"📅 Nascita: <b>{bday[2]}/{bday[1]}/{bday[0]}</b>\n" \
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
        string = "\n\n📚 <b>{0}</b>".format(materia['description'])
        result += "\n" + string if firstMateria else string
        firstMateria = False
        for prof in materia['teachers']:
            result += "\n    👤 {0}".format(prof['teacherName'])
    return result


def parseNote(data):
    if (data is None) or (not data.get('NTCL') and not data.get('NTWN') and not data.get('NTTE')):
        return "\n\n✅ Nessuna annotazione rilevata!"

    result = ""
    for nota in data['NTCL']:
        author, time, text = innerParseNotes(nota)
        result += "\n\n🚫 <b>Nota disciplinare</b> di <b>{0}</b> del {1}/{2}/{3}:\n{4}".format(author, time[2], time[1], time[0], text)

    for avviso in data['NTWN']:
        author, time, text = innerParseNotes(avviso)
        result += "\n\n⚠️ <b>Richiamo ({0})</b> di <b>{1}</b> del {2}/{3}/{4}:\n{5}".format(avviso['warningType'].lower(), author, time[2], time[1], time[0], text)

    for annotazione in data['NTTE']:
        author, time, text = innerParseNotes(annotazione)
        result += "\n\nℹ️ <b>Annotazione</b> di <b>{0}</b> del {1}/{2}/{3}:\n{4}".format(author, time[2], time[1], time[0], text)

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
            tipo = voto['componentDesc']
            time = voto['evtDate'].lower().split("-", 2)
            desc = "\n<i>{0}</i>".format(sanitize(voto['notesForFamily'])) if voto['notesForFamily'] else ""
            colore = "📗" if voto['color'] == "green" else "📕" if voto['color'] == "red" else "📘"

            if tipo == "":
                str_voto = "\n\n{0} <b>{1}</b> • {2} {3}".format(colore, value, "{0}/{1}/{2}".format(time[2], time[1], time[0]), desc)
            else:
                str_voto = "\n\n{0} <b>{1}</b> • {2} • {3} {4}".format(colore, value, tipo, "{0}/{1}/{2}".format(time[2], time[1], time[0]), desc)
            if materia not in votiOrdinati:
                votiOrdinati[materia] = []
            if materia not in media:
                media[materia] = []
            votiOrdinati[materia].append(str_voto)

            if "total" not in media:
                media["total"] = []

            if colore != "📘":
                if value[5:][-1] == "½":
                        media[materia].append(float(value[5:][:-1]) + 0.5)
                        media["total"].append(float(value[5:][:-1]) + 0.5)
                elif value[5:][-1] == "+":
                        media[materia].append(float(value[5:][:-1]) + 0.25)
                        media["total"].append(float(value[5:][:-1]) + 0.25)
                elif value[5:][-1] == "-":
                        media[materia].append(float(value[5:][:-1]) - 0.25)
                        media["total"].append(float(value[5:][:-1]) - 0.25)
                else:
                    try:
                        media[materia].append(float(value[5:]))
                        media["total"].append(float(value[5:]))
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
            string = "\n\n📚 <b>{0}\n    Media: {1} </b>".format(materia, media[materia]) + materie[materia]
            materie[materia] = string if firstMateria else "\n\n" + string
            firstMateria = False
        else:
            string = "\n\n📚 <b>{0} </b>".format(materia) + materie[materia]
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
        result += "\n\n📚 <b>Media totale: {}</b>".format(media["total"])
        result += "\n🕙 <i>Quadrimestre: {}</i>".format(user.lastPeriod)

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
        date = evento['evtDate'].split("-", 2)
        date = "{0}/{1}/{2}".format(date[2], date[1], date[0])

        if evento['evtCode'] == "ABA0":
            if not assenze:
                assenze = "\n\n\n❌ <b>Assenze</b>:"
            assenze += "\n 📌 {0}: {1}{2}".format(date, desc, toJustify)

        elif evento['evtCode'] == "ABR0":
            if not ritardi:
                ritardi = "\n\n\n🏃 <b>Ritardi</b>:"
            ritardi += "\n 📌 {0}: {1}{2}".format(date, desc, toJustify)

        elif evento['evtCode'] == "ABR1":
            if not ritardiBrevi:
                ritardiBrevi = "\n\n\n🚶 <b>Ritardi Brevi</b>:"
            ritardiBrevi += "\n 📌 {0}: {1}{2}".format(date, desc, toJustify)

        elif evento['evtCode'] == "ABU0":
            if not usciteAnticipate:
                usciteAnticipate = "\n\n\n🚪 <b>Uscite Anticipate</b>:"
            usciteAnticipate += "\n 📌 {0}: {1}{2}".format(date, desc, toJustify)

    return assenze + ritardi + ritardiBrevi + usciteAnticipate


def parseAgenda(data):
    from datetime import datetime
    if (data is None) or (not data.get('agenda')):
        return "\n🗓 L'agenda è ancora vuota."

    result = ""
    firstEvent = True
    eventslist = data['agenda']
    eventslist.sort(key=lambda x: str(x['evtDatetimeBegin']).split("T", 1)[0])
    for event in eventslist:
        date = str(event['evtDatetimeBegin']).split("T", 1)[0]
        date = date.split("-", 2)
        today = datetime.now().day
        evtDay = int(date[2])

        if evtDay != today:
            evtType = "📌" if event['evtCode'] == "AGNT" else "📝"
            separator = "\n" if firstEvent else "\n\n\n"
            firstEvent = False
            result += separator + "{0} {1}/{2}/{3} • <b>{4}</b>\n{5}".format(evtType, date[2], date[1], date[0],
                                                                             event['authorName'].title(), sanitize(event['notes']))
    return result


def parseDomani(data):
    from datetime import datetime
    if (data is None) or (not data.get('agenda')):
        return "\n🗓 Non hai compiti per domani."

    result = ""
    separator = "\n"
    for event in data['agenda']:
        evtDate = str(event['evtDatetimeBegin']).split("T", 1)[0]
        evtDay = int(evtDate.split("-", 2)[2])
        dayToCheck = datetime.now().day+1 if datetime.now().isoweekday() != 6 else datetime.now().day+2

        if evtDay == dayToCheck:
            evtType = "📌" if event['evtCode'] == "AGNT" else "📝"
            result += "{0}{1} <b>{2}</b>\n{3}".format(separator, evtType, event['authorName'].title(), sanitize(event['notes']))
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
        desc = lezione['lessonArg']
        tipo = lezione['lessonType']
        materia = lezione['subjectDesc']
        if desc == "":
            result += "✏️ {0}° ora • <b>{1}</b> di <b>{2}</b>\n\n".format(ora, tipo, materia)
        else:
            result += "✏️ {0}° ora • <b>{1}</b> di <b>{2}</b>\n{3}\n\n".format(ora, tipo, materia, sanitize(desc))
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
                result += "\n\n✉️ <a href=\"https://t.me/ClasseVivaIT_Bot?start=circ{}-{}\">{}</a>".format(evCode, pubId, title)
        else:
            if (status == 'active') and not isRead:
                result += "\n\n✉️ {}".format(title)

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
            string = "\n\n👤 <b>{0}</b>".format(prof['teacherName'])
            result += string if firstProf else "\n" + string
            firstProf = False

            firstFolder = True
            for folder in prof['folders']:
                folderName = "Altro" if folder['folderName'] == "Uncategorized" else sanitize(folder['folderName'])
                string = "\n    📂 <b>{0}</b>".format(folderName)
                result += string if firstFolder else "\n" + string
                firstFolder = False

                for upfile in folder['contents']:
                    fileName = "Senza nome" if upfile['contentName'] == "" else sanitize(upfile['contentName'])
                    fileId = upfile['contentId']
                    result += "\n        📝 <a href=\"https://t.me/ClasseVivaIT_Bot?start=file{}\">{}</a>".format(fileId, fileName)

        else:
            firstFolder = True
            for folder in prof['folders']:
                oldProfFolders = [i['folders'] for i in oldProfs if i['teacherId'] == prof['teacherId']][0]
                oldProfFolderIds = [i['folderId'] for i in oldProfFolders]
                if folder['folderId'] not in oldProfFolderIds:
                    if firstFolder:
                        string = "\n\n👤 <b>{0}</b>".format(prof['teacherName'])
                        result += string if firstProf else "\n" + string
                        firstProf = False
                    folderName = "Altro" if folder['folderName'] == "Uncategorized" else sanitize(folder['folderName'])
                    string = "\n    📂 <b>{0}</b>".format(folderName)
                    result += string if firstFolder else "\n" + string
                    firstFolder = False

                    for upfile in folder['contents']:
                        fileName = "Senza nome" if upfile['contentName'] == "" else sanitize(upfile['contentName'])
                        fileId = upfile['contentId']
                        result += "\n        📝 <a href=\"https://t.me/ClasseVivaIT_Bot?start=file{}\">{}</a>".format(fileId, fileName)

                else:
                    firstFile = True
                    for upfile in folder['contents']:
                        oldFolderFiles = [i['contents'] for i in oldProfFolders if i['folderId'] == folder['folderId']][0]
                        oldFolderFileIds = [i['contentId'] for i in oldFolderFiles]
                        if upfile['contentId'] not in oldFolderFileIds:
                            if firstFile:
                                folderName = "Altro" if folder['folderName'] == "Uncategorized" else sanitize(folder['folderName'])
                                string = "\n    📂 <b>{0}</b>".format(folderName)
                                result += string if firstFolder else "\n" + string
                                firstFolder = False
                            fileName = "Senza nome" if upfile['contentName'] == "" else sanitize(upfile['contentName'])
                            fileId = upfile['contentId']
                            result += "\n        📝 <a href=\"https://t.me/ClasseVivaIT_Bot?start=file{}\">{}</a>".format(fileId, fileName)
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
            result += "\n\n🚫 <b>Nota disciplinare</b> di <b>{0}</b> del {1}/{2}/{3}:\n{4}".format(author, time[2], time[1], time[0], text)

    for avviso in newData['NTWN']:
        if (not oldData.get('NTWN')) or (avviso not in oldData['NTWN']):
            author, time, text = innerParseNotes(avviso)
            result += "\n\n⚠️ <b>Richiamo ({0})</b> di <b>{1}</b> del {2}/{3}/{4}:\n{5}".format(avviso['warningType'].lower(), author, time[2], time[1], time[0], text)

    for annotazione in newData['NTTE']:
        if (not oldData.get('NTTE')) or (annotazione not in oldData['NTTE']):
            author, time, text = innerParseNotes(annotazione)
            result += "\n\nℹ️ <b>Annotazione</b> di <b>{0}</b> del {1}/{2}/{3}:\n{4}".format(author, time[2], time[1], time[0], text)

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
            tipo = voto['componentDesc']
            time = voto['evtDate'].lower().split("-", 2)
            desc = "\n<i>{0}</i>".format(sanitize(voto['notesForFamily'])) if voto['notesForFamily'] else ""
            colore = "📗" if voto['color'] == "green" else "📕" if voto['color'] == "red" else "📘"
            if tipo == "":
                str_voto = "\n\n{0} <b>{1}</b> • {2} {3}".format(colore, value, "{0}/{1}/{2}".format(time[2], time[1], time[0]), desc)
            else:
                str_voto = "\n\n{0} <b>{1}</b> • {2} • {3} {4}".format(colore, value, tipo, "{0}/{1}/{2}".format(time[2], time[1], time[0]), desc)
            if materia not in votiOrdinati:
                votiOrdinati[materia] = []
            votiOrdinati[materia].append(str_voto)
    if periods:
        user = User.get(chatId=chatId)
        user.lastPeriod = max(periods)

    result = ""
    firstMateria = True
    for materia, voti in votiOrdinati.items():
        string = "\n\n📚 <b>{0}</b>".format(materia)
        result += string if firstMateria else "\n\n" + string
        firstMateria = False
        for voto in voti:
            result += voto

    return result if result != "" else None


def parseNewAgenda(oldData, newData):
    if (newData is None) or (not newData.get('agenda')):
        return None
    if (oldData is None) or (not oldData.get('agenda')):
        return parseAgenda(newData)

    result = ""
    firstEvent = True
    for event in newData['agenda']:
        if event not in oldData['agenda']:
            date = str(event['evtDatetimeBegin']).split("T", 1)[0]
            date = date.split("-", 2)
            evtType = "📌" if event['evtCode'] == "AGNT" else "📝"
            separator = "\n" if firstEvent else  "\n\n\n"
            firstEvent = False
            result += separator + "{0} {1}/{2}/{3} • <b>{4}</b>\n{5}".format(evtType, date[2], date[1], date[0], event['authorName'].title(), sanitize(event['notes']))

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
                    string = "\n✉️ <a href=\"https://t.me/ClasseVivaIT_Bot?start=circ{}-{}\">{}</a>".format(evCode, pubId, title)
                    result += string if isFirst else "\n" + string
                    isFirst = False
            else:
                if (status == 'active') and not isRead:
                    string = "\n✉️ {}".format(title)
                    result += string if isFirst else "\n" + string
                    isFirst = False

    return result if result != "" else None
