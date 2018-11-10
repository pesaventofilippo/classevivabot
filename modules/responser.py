from datetime import datetime


def parseDidattica(data):
    if not data.get('didacticts'):
        return "\n\n📌 Nessun file caricato."
    result = ""
    firstProf = True
    for prof in data['didacticts']:
        if firstProf:
            firstProf = False
            result += "\n\n👤 <b>{0}</b>".format(prof['teacherName'])
        else:
            result += "\n\n\n👤 <b>{0}</b>".format(prof['teacherName'])

        firstFolder = True
        for folder in prof['folders']:
            folderName = "Altro" if folder['folderName'] == "Uncategorized" else folder['folderName']
            if firstFolder:
                firstFolder = False
                result += "\n    📂 <b>{0}</b>".format(folderName)
            else:
                result += "\n\n    📂 <b>{0}</b>".format(folderName)

            for file in folder['contents']:
                fileName = "Senza nome" if file['contentName'] == "" else file['contentName']
                result += "\n        📝 {0}".format(fileName)

    return result


def parseInfo(data):
    if not data.get('cards'):
        return "📌 Nessuna info disponibile."
    info = data['cards'][0]
    time = info['birthDate'].lower().split("-", 2)
    day = time[2]
    month = time[1]
    year = time[0]

    result = "👤 Nome: <b>{1}</b>\n" \
             "👤 Cognome: <b>{4}</b>\n" \
             "📅 Nascita: <b>{0}</b>\n" \
             "💳 Codice Fiscale: <b>{2}</b>\n" \
             "👤 Username: <b>{3}</b>\n" \
             "\n" \
             "🏫 Nome Scuola: <b>{7}</b>\n" \
             "🏫 Tipo Scuola: <b>{8}</b>\n" \
             "🏫 ID Scuola: <b>{5}</b>\n" \
             "🏛 Città: <b>{6}</b>\n" \
             "📍 Provincia: <b>{9}</b>\n" \
             "\n" \
             "👤 UserID: <b>{10}</b>\n" \
             "👤 Tipo Utente: <b>{11}</b>".format("{0}/{1}/{2}".format(day, month, year), info['firstName'], info['fiscalCode'],
                                                 info['ident'], info['lastName'], info['schCode'],
                                                 info['schCity'], info['schDedication'], info['schName'],
                                                 info['schProv'], info['usrId'], info['usrType'])
    return result


def parseMaterie(data):
    if not data.get('subjects'):
        return "\n\n📌 Nessun prof attualmente registrato."
    result = ""
    firstMateria = True
    for materia in data['subjects']:
        if firstMateria:
            firstMateria = False
            result += "\n\n\n📚 <b>{0}</b>".format(materia['description'])
        else:
            result += "\n\n📚 <b>{0}</b>".format(materia['description'])

        for prof in materia['teachers']:
            result += "\n    👤 {0}".format(prof['teacherName'])
    return result


def parseNote(data):
    result = ""

    if not data['NTCL'] and not data['NTWN'] and not data['NTTE']:
        return "\n\n✅ Nessuna annotazione rilevata!"

    for nota in data['NTCL']:
        time = nota['evtDate'].lower().split("-", 2)
        day = time[2]
        month = time[1]
        year = time[0]
        if not nota['readStatus']:
            nota['evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione <i>annotazioni</i>" \
                              "per leggere questa nota disciplinare."
        result += "\n\n🚫 <b>Nota disciplinare</b> di <b>{0}</b> del {1}:\n" \
                  "{2}".format(nota['authorName'].title(), "{0}/{1}/{2}".format(day, month, year), nota['evtText'])

    for avviso in data['NTWN']:
        time = avviso['evtDate'].lower().split("-", 2)
        day = time[2]
        month = time[1]
        year = time[0]
        if not avviso['readStatus']:
            avviso['evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione \"annotazioni\"" \
                                "per leggere questo avviso."
        result += "\n\n⚠️ <b>Richiamo ({0})</b> di <b>{1}</b> del {2}:\n" \
                  "{3}".format(avviso['warningType'].lower(), avviso['authorName'].title(), "{0}/{1}/{2}".format(day, month, year), avviso['evtText'])

    for annotazione in data['NTTE']:
        time = annotazione['evtDate'].lower().split("-", 2)
        day = time[2]
        month = time[1]
        year = time[0]
        if not annotazione['readStatus']:
            annotazione['evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione \"annotazioni\"" \
                "per leggere questa annotazione."
        result += "\n\nℹ️ <b>Annotazione</b> di <b>{0}</b> del {1}:\n" \
                  "{2}".format(annotazione['authorName'].title(), "{0}/{1}/{2}".format(day, month, year), annotazione['evtText'])

    return result


def parseVoti(data):
    if not data.get('grades'):
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
        if voto['color'] == "green":
            colore = "📗"
        elif voto['color'] == "red":
            colore = "📕"
        else:
            colore = "📘"

        if tipo == "":
            str_voto = "\n\n{0} <b>{1}</b> • {3} {4}".format(colore, value, "", "{0}/{1}/{2}".format(day, month, year),
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
                media[materia].append(float(value[5:]))

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
    if not data.get('events'):
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

            assenze += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc,
                                                             "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

        elif evento['evtCode'] == "ABR0":
            if not ritardi:
                ritardi = "\n\n\n🏃 <b>Ritardi</b>:"

            ritardi += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc,
                                                             "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

        elif evento['evtCode'] == "ABR1":
            if not ritardiBrevi:
                ritardiBrevi = "\n\n\n🚶 <b>Ritardi Brevi</b>:"

                ritardiBrevi += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc,
                                                                      "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

        elif evento['evtCode'] == "ABU0":
            if not usciteAnticipate:
                usciteAnticipate = "\n\n\n🚪 <b>Uscite Anticipate</b>:"

                usciteAnticipate += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc,
                                                                          "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

    return assenze + ritardi + ritardiBrevi + usciteAnticipate


def parseAgenda(data):
    if not data.get('agenda'):
        return "\n🗓 L'agenda è ancora vuota."

    result = ""
    firstEvent = True
    for event in data['agenda']:
        date = str(event['evtDatetimeBegin']).split("T", 1)[0]
        date = date.split("-", 2)
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
    if not data.get('agenda'):
        return "\n🗓 L'agenda è ancora vuota."

    result = ""
    firstEvent = True
    for event in data['agenda']:
        date = str(event['evtDatetimeBegin']).split("T", 1)[0]
        date = date.split("-", 2)
        today = datetime.now().day
        if int(date[2]) != today:
            evtType = "📌" if event['evtCode'] == "AGNT" else "📝"
            if firstEvent:
                firstEvent = False
                separator = "\n"
            else:
                separator = "\n\n\n"
            result += separator + "{0} <b>{1}</b>\n{2}".format(evtType, event['authorName'].title(), event['notes'])

    if result == "":
        return "\n🗓 L'agenda è ancora vuota."

    return result


def parseLezioni(data):
    if not data.get('lessons'):
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
    result = ""

    if not newData['NTCL'] and not newData['NTWN'] and not newData['NTTE']:
        return None

    for nota in newData['NTCL']:
        if (oldData is None) or (not oldData.get('NTCL')) or (nota not in oldData['NTCL']):
            time = nota['evtDate'].lower().split("-", 2)
            day = time[2]
            month = time[1]
            year = time[0]
            if not nota['readStatus']:
                nota[
                    'evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione <i>annotazioni</i>" \
                                 "per leggere questa nota disciplinare."
            result += "\n\n🚫 <b>Nota disciplinare</b> di <b>{0}</b> del {1}:\n" \
                      "{2}".format(nota['authorName'].title(), "{0}/{1}/{2}".format(day, month, year), nota['evtText'])

    for avviso in newData['NTWN']:
        if (oldData is None) or (not oldData.get('NTWN')) or (avviso not in oldData['NTWN']):
            time = avviso['evtDate'].lower().split("-", 2)
            day = time[2]
            month = time[1]
            year = time[0]
            if not avviso['readStatus']:
                avviso[
                    'evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione \"annotazioni\"" \
                                 "per leggere questo avviso."
            result += "\n\n⚠️ <b>Richiamo ({0})</b> di <b>{1}</b> del {2}:\n" \
                      "{3}".format(avviso['warningType'].lower(), avviso['authorName'].title(), "{0}/{1}/{2}".format(day, month, year),
                                   avviso['evtText'])

    for annotazione in newData['NTTE']:
        if (oldData is None) or (not oldData.get('NTTE')) or (annotazione not in oldData['NTTE']):
            time = annotazione['evtDate'].lower().split("-", 2)
            day = time[2]
            month = time[1]
            year = time[0]
            if not annotazione['readStatus']:
                annotazione[
                    'evtText'] = "Vai al <a href=\"https://web.spaggiari.eu\">registo web</a> nella sezione \"annotazioni\"" \
                                 "per leggere questa annotazione."
            result += "\n\nℹ️ <b>Annotazione</b> di <b>{0}</b> del {1}:\n" \
                      "{2}".format(annotazione['authorName'].title(), "{0}/{1}/{2}".format(day, month, year), annotazione['evtText'])

    return result if result != "" else None


def parseNewVoti(oldData, newData):
    if not newData.get('grades'):
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
            if voto['color'] == "green":
                colore = "📗"
            elif voto['color'] == "red":
                colore = "📕"
            else:
                colore = "📘"

            if tipo == "":
                str_voto = "\n\n{0} <b>{1}</b> • {3} {4}".format(colore, value, "", "{0}/{1}/{2}".format(day, month, year),
                                                                 "\n<i>{0}</i>".format(voto['notesForFamily']) if voto['notesForFamily'] else "")
            else:
                str_voto = "\n\n{0} <b>{1}</b> • {2} • {3} {4}".format(colore, value, tipo, "{0}/{1}/{2}".format(day, month, year),
                                                                       "\n<i>{0}</i>".format(voto['notesForFamily']) if voto['notesForFamily'] else "")

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
    if not newData.get('events'):
        return None

    assenze = ""
    ritardi = ""
    ritardiBrevi = ""
    usciteAnticipate = ""

    for evento in newData['events']:
        if (oldData is None) or (not oldData.get('events')) or (evento not in oldData['events']):

            if evento['justifReasonDesc'] is None:
                desc = "Altro"
            else:
                desc = evento['justifReasonDesc'].lower()

            if evento['evtCode'] == "ABA0":
                if not assenze:
                    assenze = "\n\n\n❌ <b>Assenze</b>:"

                assenze += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc,
                                                                 "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

            elif evento['evtCode'] == "ABR0":
                if not ritardi:
                    ritardi = "\n\n\n🏃 <b>Ritardi</b>:"

                ritardi += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc,
                                                                 "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

            elif evento['evtCode'] == "ABR1":
                if not ritardiBrevi:
                    ritardiBrevi = "\n\n\n🚶 <b>Ritardi Brevi</b>:"

                    ritardiBrevi += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc,
                                                                          "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

            elif evento['evtCode'] == "ABU0":
                if not usciteAnticipate:
                    usciteAnticipate = "\n\n\n🚪 <b>Uscite Anticipate</b>:"

                    usciteAnticipate += "\n\n   📌 {0}: Per \"{1}\"{2}".format(evento['evtDate'], desc,
                                                                              "\n   ⚠️ Da giustificare!" if not evento['isJustified'] else "")

    result = ""
    if assenze != "":
        result += assenze
    if ritardi != "":
        result += ritardi
    if ritardiBrevi != "":
        result += ritardiBrevi
    if usciteAnticipate != "":
        result += usciteAnticipate
    return result if result != "" else None


def parseNewAgenda(oldData, newData):
    if not newData.get('agenda'):
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
            result += separator + "{0} {1}/{2}/{3} • <b>{4}</b>\n{5}".format(evtType, date[2], date[1], date[0],
                                                                             event['authorName'].title(), event['notes'])

    return result if result != "" else None