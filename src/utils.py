import random
import re
from datetime import datetime

from faker import Faker

from src.config import DEFAULT_LANGUAGE
from src.translations import _

fake = Faker()


def get_spin_result(dice_value: int) -> str:
    values = ['b', 'g', 'l', '7']
    result = ''.join(values[((dice_value - 1) // (4 ** i)) % 4] for i in range(3))

    for i in range(len(result) - 1):
        if result[i] == result[i + 1]:
            return result[i] * result.count(result[i])

    return result


def format_spin_result(spin_result: str) -> str:
    return spin_result.replace('7', '7️⃣').replace('g', '🍇').replace('b', '🍸').replace('l', '🍋')


def format_next_refill_time(user) -> str:
    remaining_time = user.next_refill_time - datetime.utcnow()
    total_seconds = int(remaining_time.total_seconds())

    if total_seconds <= 0:
        return _("few_seconds", user.language)

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{hours:02}:{minutes:02}:{seconds:02}"


def format_tournament_info(user, tournament_stats) -> str:
    return (
        _("tournament_info", user.language,
          current_tournament_gems=tournament_stats.gems,
          current_tournament_spins=tournament_stats.spins)
        if tournament_stats else ""
    )


def format_channels_info(user, channels) -> str:
    return "\n\n".join(
        _("channel_info", user.language,
          channel_name=channel["name"],
          channel_link=channel["link"],
          subscribed='✅' if channel["subscribed"] else '🔲')
        for channel in channels
    )


def format_refill_time_info(user) -> str:
    return (
        _("refill_time_info", user.language, next_refill_time=format_next_refill_time(user))
        if user.next_refill_time else ""
    )


def format_admin_user_info(user, target) -> str:
    return (
        _("admin_user_info", user.language,
          user_id=target.chat_id,
          user_username=target.mention_username(),
          user_language=target.language)
        if user.is_admin else ""
    )


def get_spin_win_text(spin_result: str, language: str = DEFAULT_LANGUAGE) -> str:
    if len(spin_result) == 3:
        return _(f'spin_win_{spin_result}', language)

    if len(spin_result) == 2:
        return _('spin_win_two', language)


def get_random_time_this_hour() -> datetime:
    return datetime.utcnow().replace(minute=random.randint(0, 59), second=random.randint(0, 59))


def generate_random_name() -> str:
    adjective = fake.word(part_of_speech='adjective')
    noun = fake.word(part_of_speech='noun')
    return adjective.capitalize() + noun.capitalize()


def is_valid_email(email: str) -> bool:
    return re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$', email) is not None
