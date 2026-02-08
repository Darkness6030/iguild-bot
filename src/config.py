import os

from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")

BOT_ADMINS = list(eval(os.getenv("BOT_ADMINS")))
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID"))

MAIN_GROUP_ID = int(os.getenv("MAIN_GROUP_ID"))
MAIN_GROUP_URL = os.getenv("MAIN_GROUP_URL")

GAME_TOPIC_ID = int(os.getenv("GAME_TOPIC_ID"))
RESULTS_TOPIC_ID = int(os.getenv("RESULTS_TOPIC_ID"))

FEEDBACK_TOPIC_ID = int(os.getenv("FEEDBACK_TOPIC_ID"))
FEEDBACK_TOPIC_URL = os.getenv("FEEDBACK_TOPIC_URL")

DATABASE_URL = os.getenv("DATABASE_URL")
SERVER_DOMAIN = os.getenv("SERVER_DOMAIN")
SERVER_HOST = os.getenv("SERVER_HOST")
SERVER_PORT = int(os.getenv("SERVER_PORT"))

# Название таблицы с пользователями в Google Sheets
USERS_SHEET_NAME = "iguildusers"
# Название таблицы с победителями в Google Sheets
WINNERS_SHEET_NAME = "iguildwinners"

# Язык по умолчанию
DEFAULT_LANGUAGE = "en"
AVAILABLE_LANGUAGES = ["en", "hi", "es", "fr", "pt", "ru", "tr"]

# Сколько спинов добавляется по дефолту
DEFAULT_SPINS_AMOUNT = 10
# Процент начисления реферальных спинов
REFERRAL_GEMS_RATE = 0.05

# Задержка между пополнением спинов (в часах)
SPIN_REFILL_DELAY = 1

# Количество фейковых юзеров
FAKE_USERS_AMOUNT = 60
# Количество активных фейковых юзеров
ACTIVE_FAKE_USERS_AMOUNT = 12

# Награды за комбинации
SPIN_REWARDS = {
    "777": 70,
    "ggg": 30,
    "lll": 20,
    "bbb": 20,
    "77": 7,
    "gg": 3,
    "ll": 2,
    "bb": 2
}

BONUS_CHANNELS = [
    {
        "id": -1002435673190,
        "name": "Join Group",
        "link": "https://t.me/iguildforum"
    },
    {
        "id": -1001950369506,
        "name": "Join Channel",
        "link": "https://t.me/iGuild_CIS"
    },
    {
        "id": -1001751447670,
        "name": "Join Channel",
        "link": "https://t.me/iGuild_EN"
    }
]

# Эмодзи, которые выводятся при победе
WIN_EMOJIS = "💪🎉👏🔥🤘🚀🥳👍💎🕺👑💥⚽💰"
