# classevivabot
A Telegram Bot for Spaggiari's ClasseViva school E-Register

## Telegram Public Bot
[Use it on Telegram!](https://t.me/classevivait_bot)  
[Project Info & Privacy Policy](https://pesaventofilippo.com/projects/classevivabot)

## Crypting File
'modules/crypter.py', required by bot.py, is missing in the repo: that's because  
1. I don't want, for security reasons, to give the encryption key for my database, as it contains personal data of many users  
2. You can make your own information encryption method, by putting it in 'modules/crypter.py'. It must contain a "crypt" and a "decrypt" function, that will respectively encode and decode the password stored in the database.
