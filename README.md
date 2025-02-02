# Utility Bills Telegram Bot

A Telegram bot for tracking and calculating utility bills. The bot helps users track water, gas, and electricity consumption and calculates monthly payments.

## Features

- Track water, gas, and electricity (day/night) meter readings
- Calculate monthly utility bills based on current rates
- Store calculation history
- Preview calculations before confirming
- Restricted access to authorized users only
- Persistent data storage

## Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/utility-bills-bot.git
cd utility-bills-bot
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

3. Set up your bot:
- Create a new bot with [@BotFather](https://t.me/botfather) on Telegram
- Copy `secrets.example.py` to `secrets.py`
- Add your bot token to `secrets.py`
- Add allowed user IDs to `secrets.py`

4. Run the bot:
```bash
python bot.py
```

## Usage

- `/start` - Start the bot and see available commands
- `/help` - Show help information
- Select utility type from the menu to enter readings
- Use "Preview" to see calculation before confirming
- Use "Calculate" to confirm readings and advance to next month

## Data Storage

The bot stores all data locally in the `bot_data` directory:
- `confirmed_readings.json` - Historical meter readings
- `calculation_history.json` - Bill calculation history
- `month_state.json` - Current month tracking

## Requirements

- Python 3.6+
- pyTelegramBotAPI
- Other dependencies listed in requirements.txt