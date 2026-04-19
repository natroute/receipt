# receipt printer discord

who needs a screen anyway

![discord messages on a receipt](docs/demo.jpg)

unfortunately windows only. no plans to change that since the driver that this relies on is also windows only

## setup

1. obtain an Epson TM-88IV receipt printer (others might work too!)
	- i am not responsible for any abandoned bookstore ransackings
2. create a discord bot on the [developer portal](https://discord.com/developers/home)
3. in the Bot menu, toggle on the "message content" intent and copy the bot's token
4. create a file called `.env` in this directory, containing `TOKEN=[paste the token]`
5. configure the bot in `config.py` (the most important setting is the channel id)
6. run `run.bat`, or on powershell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

(PLEASE USE A VENV)

## motivation

The voices

## features

- [x] receiving and printing messages
- [x] avatars
- [x] markdown
- [x] image attachments
- [ ] other attachments (somehow)
- [ ] replies
- [ ] embeds