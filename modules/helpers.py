from time import sleep
maxMessageLength = 4096

def sendLongMessage(bot, chatId, text: str, **kwargs):
    if len(text) <= maxMessageLength:
        return bot.sendMessage(chatId, text, **kwargs)
    else:
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
