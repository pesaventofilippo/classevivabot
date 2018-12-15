def parseDidattica(data):
    if (data is None) or (not data.get('didacticts')):
        return "\n\n📌 Nessun file caricato."

    result = ""
    firstProf = True
    for prof in data['didacticts']:
        if firstProf:
            firstProf = False
            result += f"\n\n👤 <b>{prof['teacherName']}</b>"
        else:
            result += f"\n\n\n👤 <b>{prof['teacherName']}</b>"

        firstFolder = True
        for folder in prof['folders']:
            folderName = "Altro" if folder['folderName'] == "Uncategorized" else folder['folderName']
            if firstFolder:
                firstFolder = False
                result += f"\n    📂 <b>{folderName}</b>"
            else:
                result += f"\n\n    📂 <b>{folderName}</b>"

            for file in folder['contents']:
                fileName = "Senza nome" if file['contentName'] == "" else file['contentName']
                result += f"\n        📝 {fileName}"

    return result


def parseInfo(data):
    if (data is None) or (not data.get('cards')):
        return "📌 Nessuna info disponibile."

    info = data['cards'][0]
    time = info['birthDate'].lower().split("-", 2)
    day = time[2]
    month = time[1]
    year = time[0]
    result = f"👤 Nome: <b>{info['firstName']}</b>\n" \
             f"👤 Cognome: <b>{info['lastName']}</b>\n" \
             f"📅 Nascita: <b>{day}/{month}/{year}</b>\n" \
             f"💳 Codice Fiscale: <b>{info['fiscalCode']}</b>\n" \
             f"👤 Username: <b>{info['ident']}</b>\n" \
             "\n" \
             f"🏫 Nome Scuola: <b>{info['schName']}</b>\n" \
             f"🏫 Tipo Scuola: <b>{info['schDedication']}</b>\n" \
             f"🏫 ID Scuola: <b>{info['schCode']}</b>\n" \
             f"🏛 Città: <b>{info['schCity']}</b>\n" \
             f"📍 Provincia: <b>{info['schProv']}</b>\n" \
             "\n" \
             f"👤 UserID: <b>{info['usrId']}</b>\n" \
             f"👤 Tipo Utente: <b>{info['usrType']}</b>"
    return result


def parseMaterie(data):
    if (data is None) or (not data.get('subjects')):
        return "\n\n📌 Nessun prof attualmente registrato."

    result = ""
    firstMateria = True
    for materia in data['subjects']:
        if firstMateria:
            firstMateria = False
            result += f"\n\n\n📚 <b>{materia['description']}</b>"
        else:
            result += f"\n\n📚 <b>{materia['description']}</b>"

        for prof in materia['teachers']:
            result += f"\n    👤 {prof['teacherName']}"
    return result


def parseNote(data):
    if (data is None) or (not data.get('NTCL') and not data.get('NTWN') and not data.get('NTTE')):
        return "\n\n✅ Nessuna annotazione rilevata!"

    result = ""
    for nota in data['NTCL']:
        time = nota['evtDate'].lower().split("-", 2)
        day = time[2]
        month = time[1]
        year = time[0]
        if not nota['readStatus']:
            nota['evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione <i>annotazioni</i> per leggere questa nota disciplinare."
        result += f"\n\n🚫 <b>Nota disciplinare</b> di <b>{nota['authorName'].title()}</b> del {day}/{month}/{year}:\n{nota['evtText']}"

    for avviso in data['NTWN']:
        time = avviso['evtDate'].lower().split("-", 2)
        day = time[2]
        month = time[1]
        year = time[0]
        if not avviso['readStatus']:
            avviso['evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione \"annotazioni\" per leggere questo avviso."
        result += f"\n\n⚠️ <b>Richiamo ({avviso['warningType'].lower()})</b> di <b>{avviso['authorName'].title()}</b> del {day}/{month}/{year}:\n{avviso['evtText']}"

    for annotazione in data['NTTE']:
        time = annotazione['evtDate'].lower().split("-", 2)
        day = time[2]
        month = time[1]
        year = time[0]
        if not annotazione['readStatus']:
            annotazione['evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione \"annotazioni\" per leggere questa annotazione."
        result += f"\n\nℹ️ <b>Annotazione</b> di <b>{annotazione['authorName'].title()}</b> del {day}/{month}/{year}:\n{annotazione['evtText']}"

    return result


def parseVoti(data):
    if (data is None) or (not data.get('grades')):
        return "\n📕 Non hai ancora nessun voto!"

    votiOrdinati = {}
    media = {}
    for voto in data['grades']:
        materia = voto['subjectDesc']
        value = "Voto " + voto['displayValue']
        tipo = voto['componentDesc']
        time = voto['evtDate'].lower().split("-", 2)
        day = time[2]
        month = time[1]
        year = time[0]
        colore = "📗" if voto['color'] == "green" else "📕" if voto['color'] == "red" else "📘"

        if tipo == "":
            str_voto = "\n\n{0} <b>{1}</b> • {2} {3}".format(colore, value, "{0}/{1}/{2}".format(day, month, year),
                                                             "\n<i>{0}</i>".format(voto['notesForFamily']) if voto['notesForFamily'] else "")
        else:
            str_voto = "\n\n{0} <b>{1}</b> • {2} • {3} {4}".format(colore, value, tipo, "{0}/{1}/{2}".format(day, month, year),
                                                                   "\n<i>{0}</i>".format(voto['notesForFamily']) if voto['notesForFamily'] else "")
        if materia not in votiOrdinati:
            votiOrdinati[materia] = []
        if materia not in media:
            media[materia] = []
        votiOrdinati[materia].append(str_voto)

        if colore != "📘":
            if value[5:][-1] == "½":
                    media[materia].append(float(value[5:][:-1]) + 0.5)
            elif value[5:][-1] == "+":
                    media[materia].append(float(value[5:][:-1]) + 0.25)
            elif value[5:][-1] == "-":
                    media[materia].append(float(value[5:][:-1]) - 0.25)
            else:
                try:
                    media[materia].append(float(value[5:]))
                except ValueError:
                    pass

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
            if firstMateria:
                firstMateria = False
                materie[materia] = "\n\n📚 <b>{0}\n    Media: {1} </b>".format(materia, media[materia]) + materie[materia]
            else:
                materie[materia] = "\n\n\n\n📚 <b>{0}\n    Media: {1} </b>".format(materia, media[materia]) + materie[materia]
        else:
            if firstMateria:
                firstMateria = False
                materie[materia] = "\n\n📚 <b>{0} </b>".format(materia) + materie[materia]
            else:
                materie[materia] = "\n\n\n\n📚 <b>{0} </b>".format(materia) + materie[materia]

    result = ""
    for materia in materie:
        result += materie[materia]

    return result


def parseAssenze(data):
    if (data is None) or (not data.get('events')):
        return "\n\n✅ Nessuna assenza/ritardo rilevati!"

    assenze = ""
    ritardi = ""
    ritardiBrevi = ""
    usciteAnticipate = ""

    for evento in data['events']:
        if evento['justifReasonDesc'] is None:
            desc = "Altro"
        else:
            desc = evento['justifReasonDesc'].lower()

        if evento['evtCode'] == "ABA0":
            if not assenze:
                assenze = "\n\n\n❌ <b>Assenze</b>:"
            assenze += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc, "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

        elif evento['evtCode'] == "ABR0":
            if not ritardi:
                ritardi = "\n\n\n🏃 <b>Ritardi</b>:"
            ritardi += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc, "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

        elif evento['evtCode'] == "ABR1":
            if not ritardiBrevi:
                ritardiBrevi = "\n\n\n🚶 <b>Ritardi Brevi</b>:"
            ritardiBrevi += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc, "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

        elif evento['evtCode'] == "ABU0":
            if not usciteAnticipate:
                usciteAnticipate = "\n\n\n🚪 <b>Uscite Anticipate</b>:"
            usciteAnticipate += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc, "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

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
            if firstEvent:
                firstEvent = False
                separator = "\n"
            else:
                separator = "\n\n\n"
            result += separator + "{0} {1}/{2}/{3} • <b>{4}</b>\n{5}".format(evtType, date[2], date[1], date[0],
                                                                             event['authorName'].title(), event['notes'])

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
        dayToCheck = datetime.now().day + 1

        if evtDay == dayToCheck:
            evtType = "📌" if event['evtCode'] == "AGNT" else "📝"
            result += "{0}{1} <b>{2}</b>\n{3}".format(separator, evtType, event['authorName'].title(), event['notes'])
            separator = "\n\n\n"

    if result == "":
        return "\n🗓 Non hai compiti per domani."

    return result


def parseLezioni(data):
    if (data is None) or (not data.get('lessons')):
        return "🎈 Nessuna lezione, per oggi."

    result = ""
    for lezione in data['lessons']:
        ora = lezione['evtHPos']
        descrizione = lezione['lessonArg']
        tipo = lezione['lessonType']
        materia = lezione['subjectDesc']

        if descrizione == "":
            result += "✏️ {0}° ora • <b>{1}</b> di <b>{2}</b>\n\n".format(ora, tipo, materia)
        else:
            result += "✏️ {0}° ora • <b>{1}</b> di <b>{2}</b>\n{3}\n\n".format(ora, tipo, materia, descrizione)

    return result


def parseNewNote(oldData, newData):
    if (newData is None) or (not newData.get('NTCL') and not newData.get('NTWN') and not newData.get('NTTE')):
        return None

    result = ""
    for nota in newData['NTCL']:
        if (oldData is None) or (not oldData.get('NTCL')) or (nota not in oldData['NTCL']):
            time = nota['evtDate'].lower().split("-", 2)
            day = time[2]
            month = time[1]
            year = time[0]
            if not nota['readStatus']:
                nota['evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione <i>annotazioni</i> per leggere questa nota disciplinare."
            result += "\n\n🚫 <b>Nota disciplinare</b> di <b>{0}</b> del {1}:\n {2}".format(nota['authorName'].title(), "{0}/{1}/{2}".format(day, month, year), nota['evtText'])

    for avviso in newData['NTWN']:
        if (oldData is None) or (not oldData.get('NTWN')) or (avviso not in oldData['NTWN']):
            time = avviso['evtDate'].lower().split("-", 2)
            day = time[2]
            month = time[1]
            year = time[0]
            if not avviso['readStatus']:
                avviso['evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione \"annotazioni\" per leggere questo avviso."
            result += "\n\n⚠️ <b>Richiamo ({0})</b> di <b>{1}</b> del {2}:\n{3}".format(avviso['warningType'].lower(), avviso['authorName'].title(), "{0}/{1}/{2}".format(day, month, year), avviso['evtText'])

    for annotazione in newData['NTTE']:
        if (oldData is None) or (not oldData.get('NTTE')) or (annotazione not in oldData['NTTE']):
            time = annotazione['evtDate'].lower().split("-", 2)
            day = time[2]
            month = time[1]
            year = time[0]
            if not annotazione['readStatus']:
                annotazione['evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione \"annotazioni\" per leggere questa annotazione."
            result += "\n\nℹ️ <b>Annotazione</b> di <b>{0}</b> del {1}:\n{2}".format(annotazione['authorName'].title(), "{0}/{1}/{2}".format(day, month, year), annotazione['evtText'])

    return result if result != "" else None


def parseNewVoti(oldData, newData):
    if (newData is None) or (not newData.get('grades')):
        return None

    votiOrdinati = {}
    for voto in newData['grades']:
        if (oldData is None) or (not oldData.get('grades')) or (voto not in oldData['grades']):
            materia = voto['subjectDesc']
            value = "Voto " + voto['displayValue']
            tipo = voto['componentDesc']
            time = voto['evtDate'].lower().split("-", 2)
            day = time[2]
            month = time[1]
            year = time[0]
            colore = "📗" if voto['color'] == "green" else "📕" if voto['color'] == "red" else "📘"

            if tipo == "":
                str_voto = "\n\n{0} <b>{1}</b> • {2} {3}".format(colore, value, "{0}/{1}/{2}".format(day, month, year), "\n<i>{0}</i>".format(voto['notesForFamily']) if voto['notesForFamily'] else "")
            else:
                str_voto = "\n\n{0} <b>{1}</b> • {2} • {3} {4}".format(colore, value, tipo, "{0}/{1}/{2}".format(day, month, year), "\n<i>{0}</i>".format(voto['notesForFamily']) if voto['notesForFamily'] else "")

            if materia not in votiOrdinati:
                votiOrdinati[materia] = []
            votiOrdinati[materia].append(str_voto)

    result = ""
    firstMateria = True
    for materia, voti in votiOrdinati.items():
        if firstMateria:
            firstMateria = False
            result += "\n\n📚 <b>{0}</b>".format(materia)
        else:
            result += "\n\n\n\n📚 <b>{0}</b>".format(materia)
        for voto in voti:
            result += voto

    return result if result != "" else None


def parseNewAssenze(oldData, newData):
    if (newData is None) or (not newData.get('events')):
        return None

    assenze = ""
    ritardi = ""
    ritardiBrevi = ""
    usciteAnticipate = ""

    for evento in newData['events']:
        if (oldData is None) or (not oldData.get('events')) or (evento not in oldData['events']):
            desc = "Altro" if evento['justifReasonDesc'] is None else evento['justifReasonDesc'].lower()
            if evento['evtCode'] == "ABA0":
                if not assenze:
                    assenze = "\n\n\n❌ <b>Assenze</b>:"
                assenze += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc, "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

            elif evento['evtCode'] == "ABR0":
                if not ritardi:
                    ritardi = "\n\n\n🏃 <b>Ritardi</b>:"
                ritardi += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc, "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

            elif evento['evtCode'] == "ABR1":
                if not ritardiBrevi:
                    ritardiBrevi = "\n\n\n🚶 <b>Ritardi Brevi</b>:"
                ritardiBrevi += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc, "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

            elif evento['evtCode'] == "ABU0":
                if not usciteAnticipate:
                    usciteAnticipate = "\n\n\n🚪 <b>Uscite Anticipate</b>:"
                usciteAnticipate += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc, "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

    result = assenze + ritardi + ritardiBrevi + usciteAnticipate
    return result if result != "" else None


def parseNewAgenda(oldData, newData):
    if (newData is None) or (not newData.get('agenda')):
        return None

    result = ""
    firstEvent = True
    for event in newData['agenda']:
        if (oldData is None) or (not oldData.get('agenda')) or (event not in oldData['agenda']):
            date = str(event['evtDatetimeBegin']).split("T", 1)[0]
            date = date.split("-", 2)
            evtType = "📌" if event['evtCode'] == "AGNT" else "📝"
            if firstEvent:
                firstEvent = False
                separator = "\n"
            else:
                separator = "\n\n\n"
            result += separator + "{0} {1}/{2}/{3} • <b>{4}</b>\n{5}".format(evtType, date[2], date[1], date[0], event['authorName'].title(), event['notes'])

    return result if result != "" else None