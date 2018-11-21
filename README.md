# classevivabot
A Telegram Bot for Spaggiari's ClasseViva school E-Register


## Telegram Public Bot
[Use it on Telegram](https://t.me/classevivait_bot)!


## Crypting File
'modules/crypter.py', required by bot.py, is missing in the repo: that's because
1. I don't want, for security reasons, to give the encryption key for my database, as it contains personal data of many users
2. You can make your own information encryption method, putting it in 'modules/crypt.py'. It must contain a "crypt" and a "decrypt" functions, that will respectively encode and decode the password stored in the database.