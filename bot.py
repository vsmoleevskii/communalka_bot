import telebot
from telebot import types
from secrets import secrets
from datetime import datetime

# Bot setup
token = secrets.get('BOT_API_TOKEN')
bot = telebot.TeleBot(token)

# Initial readings for November 2024
INITIAL_READINGS = {
    '📊 Water': 71,
    '🔥 Gas': 1366
}

# Enhanced in-memory storage
user_readings = {}  # Store current readings
user_states = {}    # Store user states
confirmed_readings = {}  # Store confirmed readings after calculation {user_id: {month: {utility: reading}}}
calculation_history = {}  # Store calculation history

# Utility rates
RATES = {
    '📊 Water': 205.992,
    '⚡ Day': 53.48,
    '⚡ Night': 43.48,
    '🔥 Gas': 143.7
}

class MonthManager:
    def __init__(self):
        self.months = {
            1: 'Январь',
            2: 'Февраль',
            3: 'Март',
            4: 'Апрель',
            5: 'Май',
            6: 'Июнь',
            7: 'Июль',
            8: 'Август',
            9: 'Сентябрь',
            10: 'Октябрь',
            11: 'Ноябрь',
            12: 'Декабрь'
        }
        self.current_month = 12  # Start with December 2024
        self.current_year = 2024

    def get_current_month(self):
        return self.months[self.current_month]

    def get_previous_month(self):
        if self.current_month == 1:  # January
            return 'Декабрь'
        else:
            prev_month = self.current_month - 1
            return self.months[prev_month]
        
    def get_current_year(self):
        return self.current_year
        
    def advance_month(self):
        if self.current_month == 12:  # December to January
            self.current_month = 1
            self.current_year = 2025
        elif self.current_month < 12:  # Any other month
            self.current_month += 1

month_manager = MonthManager()

def create_markup():
    """Create keyboard markup with utility options"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    water_btn = types.KeyboardButton('📊 Water')
    electricity_day_btn = types.KeyboardButton('⚡ Day')
    electricity_night_btn = types.KeyboardButton('⚡ Night')
    gas_btn = types.KeyboardButton('🔥 Gas')
    calculate_btn = types.KeyboardButton('💰 Calculate')
    preview_btn = types.KeyboardButton('👀 Preview')
    history_btn = types.KeyboardButton('📜 History')
    markup.row(water_btn)
    markup.row(electricity_day_btn, electricity_night_btn)
    markup.row(gas_btn)
    markup.row(preview_btn, calculate_btn)
    markup.row(history_btn)
    return markup

def get_previous_reading(user_id, utility_type):
    """Get previous month's reading for utility"""
    # For first time electricity readings
    if utility_type in ['⚡ Day', '⚡ Night']:
        if user_id not in confirmed_readings:
            return None
        for month_data in reversed(list(confirmed_readings[user_id].values())):
            if utility_type in month_data:
                return month_data[utility_type]
        return None
    
    # For other utilities
    if user_id in confirmed_readings:
        # Look for the most recent confirmed reading
        for month_data in reversed(list(confirmed_readings[user_id].values())):
            if utility_type in month_data:
                return month_data[utility_type]
    
    # If no confirmed readings found, return initial reading
    return INITIAL_READINGS.get(utility_type, 0)

@bot.message_handler(commands=['start'])
def start_message(message):
    current_month = month_manager.get_current_month()
    current_year = month_manager.get_current_year()
    
    welcome_text = f"""
👋 Добро пожаловать в бот учета коммунальных услуг!

Текущий месяц: {current_month} {current_year}

Показания за ноябрь 2024:
📊 Water: {INITIAL_READINGS['📊 Water']}
⚡ Day/Night: Нет исторических данных
🔥 Gas: {INITIAL_READINGS['🔥 Gas']}

Выберите опцию из меню ниже:

📊 Water - Показания воды (драм/м3)
⚡ Day - Показания электричества дневной тариф (драм/кВт)
⚡ Night - Показания электричества ночной тариф (драм/кВт)
🔥 Gas - Показания газа (драм/м3)
💰 Calculate - Рассчитать общую сумму
📜 History - История расчетов
    """
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_markup())
    
    # Initialize storage for this user
    if message.chat.id not in user_readings:
        user_readings[message.chat.id] = {}
    if message.chat.id not in calculation_history:
        calculation_history[message.chat.id] = []

@bot.message_handler(commands=['help'])
def help_message(message):
    current_month = month_manager.get_current_month()
    current_year = month_manager.get_current_year()
    help_text = f"""
🔍 Как пользоваться ботом:

Текущий месяц: {current_month} {current_year}

1. Введите показания счетчиков:
   📊 Water - Вода (205.992 драм/м3)
   ⚡ Day - Электричество день (53.48 драм/кВт)
   ⚡ Night - Электричество ночь (43.48 драм/кВт)
   🔥 Gas - Газ (143.7 драм/м3)

2. Будет рассчитана разница с предыдущим месяцем

3. Нажмите 💰 Calculate для расчета суммы

/start - Перезапустить бота
/help - Показать эту справку
    """
    bot.send_message(message.chat.id, help_text)

def validate_reading(text):
    """Validate that the reading is a positive number"""
    try:
        reading = float(text)
        if reading < 0:
            return False, "Показания не могут быть отрицательными"
        if reading > 99999:
            return False, "Показания кажутся слишком большими"
        return True, reading
    except ValueError:
        return False, "Пожалуйста, введите корректное число"

@bot.message_handler(func=lambda message: message.text == '💰 Calculate')
def handle_calculation(message):
    if message.chat.id in user_states:
        del user_states[message.chat.id]
        
    if message.chat.id not in user_readings or not user_readings[message.chat.id]:
        bot.reply_to(message, "❌ Нет сохраненных показаний. Пожалуйста, внесите показания сначала!")
        return

    current_month = month_manager.get_current_month()
    current_year = month_manager.get_current_year()
    
    # Calculate consumptions based on previous confirmed readings
    consumptions = {}
    readings = user_readings[message.chat.id]
    response = f"💰 Расчет платежа за {current_month} {current_year}:\n\n"
    total = 0

    for utility, current_reading in readings.items():
        previous_reading = get_previous_reading(message.chat.id, utility)
        consumption = current_reading - (previous_reading or 0)
        consumptions[utility] = consumption
        cost = consumption * RATES[utility]
        response += f"{utility}: {consumption} × {RATES[utility]} = {cost:.2f} драм\n"
        total += cost

    response += f"\n📊 Общая сумма: {total:.2f} драм"

    # Store confirmed readings
    if message.chat.id not in confirmed_readings:
        confirmed_readings[message.chat.id] = {}
    month_key = f"{current_month} {current_year}"
    confirmed_readings[message.chat.id][month_key] = readings.copy()
    
    # Store calculation in history
    timestamp = datetime.now().strftime('%d.%m.%Y %H:%M')
    calculation = {
        'timestamp': timestamp,
        'month': month_key,
        'readings': consumptions,
        'total': total
    }
    
    if message.chat.id not in calculation_history:
        calculation_history[message.chat.id] = []
    
    calculation_history[message.chat.id].append(calculation)
    calculation_history[message.chat.id] = calculation_history[message.chat.id][-5:]
    
    bot.reply_to(message, response)
    
    # Clear current readings and advance month
    user_readings[message.chat.id] = {}
    month_manager.advance_month()

# Add preview calculation handler
@bot.message_handler(func=lambda message: message.text == '👀 Preview')
def handle_preview(message):
    if message.chat.id in user_states:
        del user_states[message.chat.id]
        
    if message.chat.id not in user_readings or not user_readings[message.chat.id]:
        bot.reply_to(message, "❌ Нет сохраненных показаний. Пожалуйста, внесите показания сначала!")
        return

    current_month = month_manager.get_current_month()
    current_year = month_manager.get_current_year()
    
    # Calculate consumptions based on previous confirmed readings
    consumptions = {}
    readings = user_readings[message.chat.id]
    response = f"👀 Предварительный расчет за {current_month} {current_year}:\n\n"
    total = 0

    for utility, current_reading in readings.items():
        previous_reading = get_previous_reading(message.chat.id, utility)
        consumption = current_reading - (previous_reading or 0)
        consumptions[utility] = consumption
        cost = consumption * RATES[utility]
        response += f"{utility}: {consumption} × {RATES[utility]} = {cost:.2f} драм\n"
        total += cost

    response += f"\n📊 Предварительная сумма: {total:.2f} драм\n"
    response += "\nДля подтверждения показаний и перехода к следующему месяцу нажмите '💰 Calculate'"

    bot.reply_to(message, response)

@bot.message_handler(func=lambda message: message.text == '📜 History')
def show_history(message):
    # Clear any existing state
    if message.chat.id in user_states:
        del user_states[message.chat.id]
        
    if message.chat.id not in calculation_history or not calculation_history[message.chat.id]:
        bot.reply_to(message, "📜 История расчетов пуста")
        return

    response = "📜 История последних расчетов:\n\n"
    for calc in reversed(calculation_history[message.chat.id]):
        response += f"🕒 {calc['timestamp']} ({calc['month']})\n"
        for utility, consumption in calc['readings'].items():
            cost = consumption * RATES[utility]
            response += f"{utility}: {consumption} × {RATES[utility]} = {cost:.2f} драм\n"
        response += f"Итого: {calc['total']:.2f} драм\n\n"

    bot.reply_to(message, response)

@bot.message_handler(func=lambda message: message.text in ['📊 Water', '⚡ Day', '⚡ Night', '🔥 Gas'])
def handle_reading_selection(message):
    reading_type = message.text
    current_month = month_manager.get_current_month()
    current_year = month_manager.get_current_year()
    previous_reading = get_previous_reading(message.chat.id, reading_type)
    
    user_states[message.chat.id] = reading_type
    
    if reading_type in ['⚡ Day', '⚡ Night'] and previous_reading is None:
        bot.reply_to(message, 
                    f"Введите показания {reading_type} за {current_month} {current_year}:\n"
                    f"Предыдущие показания: Нет исторических данных")
    else:
        bot.reply_to(message, 
                    f"Введите показания {reading_type} за {current_month} {current_year}:\n"
                    f"Предыдущие показания: {previous_reading}")

@bot.message_handler(func=lambda message: message.chat.id in user_states and message.text not in ['💰 Calculate', '📜 History'])
def handle_reading_input(message):
    reading_type = user_states[message.chat.id]
    is_valid, current_reading = validate_reading(message.text)
    
    if not is_valid:
        bot.reply_to(message, f"❌ {current_reading}")
        return

    if message.chat.id not in user_readings:
        user_readings[message.chat.id] = {}
    
    previous_reading = get_previous_reading(message.chat.id, reading_type)
    
    if reading_type in ['⚡ Day', '⚡ Night'] and previous_reading is None:
        response = f"✅ Показания {reading_type} приняты: {current_reading}\n"
        response += "Расход будет рассчитан со следующего месяца"
        user_readings[message.chat.id][reading_type] = current_reading  # Store current reading
        bot.reply_to(message, response)
        del user_states[message.chat.id]
        return
    
    consumption = current_reading - previous_reading
    
    if consumption < 0:
        bot.reply_to(message, "❌ Новые показания меньше предыдущих!")
        return
    
    # Store current reading and calculate consumption
    user_readings[message.chat.id][reading_type] = current_reading  # Store the actual reading
    
    cost = consumption * RATES[reading_type]
    current_month = month_manager.get_current_month()
    current_year = month_manager.get_current_year()
    response = f"✅ Показания {reading_type} за {current_month} {current_year} приняты:\n"
    response += f"Предыдущие: {previous_reading}\n"
    response += f"Текущие: {current_reading}\n"
    response += f"Расход: {consumption}\n"
    response += f"Сумма: {cost:.2f} драм"
    
    bot.reply_to(message, response)
    del user_states[message.chat.id]

# Handle unknown commands last
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    if message.chat.id in user_states:
        bot.reply_to(message, "❌ Пожалуйста, введите корректное число")
    else:
        bot.reply_to(message, "⚠️ Неизвестная команда. Используйте меню или наберите /help")

# Start the bot
if __name__ == '__main__':
    print("Bot started...")
    bot.polling(none_stop=True, interval=0)