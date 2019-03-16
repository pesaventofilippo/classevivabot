from time import sleep
maxMessageLenght = 4096

def sendLongMessage(bot, chatId, text: str, **kwargs):
    if len(text) <= maxMessageLenght:
        return bot.sendMessage(chatId, text, **kwargs)
    else:
        parts = []
        while len(text) > 0:
            if len(text) > maxMessageLenght:
                part = text[:maxMessageLenght]
                first_lnbr = part.rfind('\n')
                if first_lnbr != -1:
                    parts.append(part[:first_lnbr])
                    text = text[(first_lnbr + 1):]
                else:
                    parts.append(part)
                    text = text[maxMessageLenght:]
            else:
                parts.append(text)
                break

        msg = None
        for part in parts:
            msg = bot.sendMessage(chatId, part, **kwargs)
            sleep(0.5)
        return msg