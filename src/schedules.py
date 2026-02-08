import asyncio
import math
import random
from datetime import timedelta, datetime

from src import database
from src import handlers
from src.config import DEFAULT_SPINS_AMOUNT, SPIN_REWARDS, ACTIVE_FAKE_USERS_AMOUNT, WIN_EMOJIS, SPIN_REFILL_DELAY, GAME_TOPIC_ID, USERS_SHEET_NAME, REFERRAL_GEMS_RATE, MAIN_GROUP_ID
from src.keyboards import create_send_email_keyboard, create_play_group_keyboard, create_tournament_keyboard
from src.sheets import update_google_sheet
from src.translations import _
from src.utils import get_spin_result, get_spin_win_text, format_spin_result, get_random_time_this_hour, format_refill_time_info, format_tournament_info


async def update_spins_left():
    now = datetime.utcnow()

    for user in database.get_all_users(is_fake=False, is_banned=False):
        if not user.next_refill_time or user.next_refill_time >= now:
            continue

        referral_spins_limit = await handlers.get_bonus_spins_limit(user)
        if user.spins_left < referral_spins_limit:
            user.spins_left = referral_spins_limit
            user.next_refill_time = now + timedelta(hours=SPIN_REFILL_DELAY)

            await asyncio.sleep(0.1)
            await handlers.send_message(
                user.chat_id,
                _("spins_refilled", user.language,
                  anon_name=user.format_anon_name(),
                  spins_left=user.spins_left,
                  refill_time_info=format_refill_time_info(user))
            )
        else:
            user.next_refill_time = None

    database.commit()


async def update_spins_limit():
    now = datetime.utcnow()

    for user in database.get_all_users(is_fake=False, is_banned=False):
        if not user.last_spin_time:
            continue

        time_since_last_spin = now - user.last_spin_time
        if time_since_last_spin >= timedelta(hours=24):
            user.spins_limit = DEFAULT_SPINS_AMOUNT
        else:
            user.spins_limit += DEFAULT_SPINS_AMOUNT

    database.commit()


async def update_fake_autospins():
    now = datetime.utcnow()

    user = next((user for user in database.get_all_users(is_fake=True, is_active=True) if user.next_autospin_time < now), None)
    if not user:
        return

    for spin in range(random.randint(5, 10)):
        spin_result = get_spin_result(random.randint(1, 64))
        spin_reward = SPIN_REWARDS.get(spin_result, 0)

        database.record_user_spin(user)
        database.credit_user_spin_reward(user, spin_reward, spin_result == "777")

        if spin_reward and (len(spin_result) == 3 or (len(spin_result) == 2 and random.random() <= 0.2)):
            if len(spin_result) == 3:
                await handlers.send_group_message(GAME_TOPIC_ID, random.choice(WIN_EMOJIS))

            await handlers.send_group_message(
                GAME_TOPIC_ID,
                _("spin_win_group",
                  random_text=get_spin_win_text(spin_result),
                  spin_result=format_spin_result(spin_result),
                  spin_reward=spin_reward,
                  anon_name=user.format_anon_name())
            )

    user.spins_left = DEFAULT_SPINS_AMOUNT
    user.next_autospin_time = get_random_time_this_hour() + timedelta(hours=1)

    database.commit()


async def send_spin_warnings():
    now = datetime.utcnow()
    warning_levels = [
        (1, 12),
        (2, 24),
        (3, 72)
    ]

    current_tournament = database.get_current_tournament()
    if not current_tournament:
        return

    for user in database.get_all_users(is_fake=False, is_banned=False):
        if not user.last_spin_time or user.last_spin_time.date() == now.date():
            continue

        time_since_last_spin = now - user.last_spin_time
        current_tournament_stats = database.get_user_tournament_stats(user.id, current_tournament.id)

        for warning_level, delta_hours in reversed(warning_levels):
            if time_since_last_spin >= timedelta(hours=delta_hours) and user.warning_level < warning_level:
                await asyncio.sleep(0.1)

                if user.last_warning_message_id:
                    await handlers.delete_message(user.chat_id, user.last_warning_message_id)

                warning_message = await handlers.send_message(
                    user.chat_id,
                    _("no_spins_warning", user.language,
                      anon_name=user.format_anon_name(),
                      spins_left=user.spins_left,
                      tournament_info=format_tournament_info(user, current_tournament_stats))
                )

                user.warning_level = warning_level
                user.last_warning_message_id = warning_message.message_id
                break

    database.commit()


async def start_tournament():
    fake_users = database.get_all_users(is_fake=True)
    previous_winners = [user for user in fake_users if user.is_previous_tournament_winner]

    remaining_users = max(0, ACTIVE_FAKE_USERS_AMOUNT - len(previous_winners))
    active_users = random.sample(
        [user for user in fake_users if not user.is_previous_tournament_winner], remaining_users
    )

    for user in fake_users:
        user.is_active = user.is_previous_tournament_winner or user in active_users
        user.next_autospin_time = get_random_time_this_hour()

    database.commit()
    database.reset_spins_for_all_users(DEFAULT_SPINS_AMOUNT)

    new_tournament = database.start_new_tournament()
    tournament_start_date = new_tournament.start_date.strftime('%Y/%m/%d')

    for user in database.get_all_users(is_fake=False, is_banned=False):
        await asyncio.sleep(0.1)
        await handlers.send_message(
            user.chat_id,
            _("tournament_started", user.language, anon_name=user.format_anon_name(), tournament_start_date=tournament_start_date),
            reply_markup=create_tournament_keyboard(user.language)
        )

    await handlers.send_group_message(GAME_TOPIC_ID, "📣")
    group_message = await handlers.send_group_message(
        GAME_TOPIC_ID,
        _("tournament_started_group"),
        image_path="assets/images/iguild_challenge.png",
        reply_markup=create_play_group_keyboard()
    )

    result_message = await group_message.forward(MAIN_GROUP_ID)
    await group_message.pin()
    await result_message.pin()


async def end_tournament():
    current_tournament = database.end_current_tournament()
    if not current_tournament:
        return

    leaderboard = database.get_tournament_leaderboard(current_tournament.id)[:3]
    if not leaderboard:
        return

    user_place_keys = ['first_place', 'second_place', 'third_place']
    group_place_keys = ['first_place_group', 'second_place_group', 'third_place_group']

    leaderboard_entries = [
        _(user_place_keys[place], stats.user.language, anon_name=stats.user.mention_anon_name(), gems=stats.gems)
        for place, stats in enumerate(leaderboard)
    ]

    tournament_end_date = current_tournament.end_date
    tournament_start_date = datetime.utcnow() + timedelta(days=(7 - datetime.utcnow().weekday()) % 7)

    for user in database.get_all_users(is_banned=False):
        user_place, user_stats = next(((place, stats) for place, stats in enumerate(leaderboard, 1) if stats.user == user), (None, None))
        message_key = 'tournament_ended_winner' if user_place else 'tournament_ended_loser'

        if user_place:
            user.tournament_wins += 1
            if user_place == 1:
                if user.is_previous_tournament_winner:
                    user.tournament_king_wins += 1
                    user.max_tournament_king_wins = max(user.max_tournament_king_wins, user.tournament_king_wins)
                user.is_previous_tournament_winner = True
            else:
                user.tournament_king_wins = 0
                user.is_previous_tournament_winner = False

            if user.referrer:
                user.referrer.gems_total += math.ceil(user_stats.gems * REFERRAL_GEMS_RATE)
        else:
            user.tournament_king_wins = 0
            user.is_previous_tournament_winner = False

        database.commit()

        if user.is_fake:
            continue

        await asyncio.sleep(0.1)
        await handlers.send_message(
            user.chat_id,
            _(message_key, user.language,
              tournament_end_date=tournament_end_date.strftime('%Y/%m/%d'),
              tournament_start_date=tournament_start_date.strftime('%Y/%m/%d'),
              leaderboard_text="\n".join(leaderboard_entries)),
            reply_markup=create_send_email_keyboard(user.language, current_tournament.id) if user_place else create_tournament_keyboard(user.language)
        )

    group_leaderboard_entries = [
        _(group_place_keys[place], anon_name=stats.user.mention_anon_name(), gems=stats.gems)
        for place, stats in enumerate(leaderboard)
    ]

    await handlers.send_group_message(GAME_TOPIC_ID, "🏁")
    group_message = await handlers.send_group_message(
        GAME_TOPIC_ID,
        _("tournament_ended_group",
          tournament_end_date=tournament_end_date.strftime('%Y/%m/%d'),
          leaderboard_text="\n\n".join(group_leaderboard_entries)),
        image_path="assets/images/iguild_awards.png",
        reply_markup=create_play_group_keyboard()
    )

    result_message = await group_message.forward(MAIN_GROUP_ID)
    await group_message.pin()
    await result_message.pin()


async def unload_to_google_sheets():
    users = database.get_all_users(is_fake=False)
    if not users:
        return

    rows = []
    for user in users:
        rows.append({
            'ID': user.chat_id,
            'Username': user.username,
            'Language': user.language,
            'Created At': user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Anon Name': user.anon_name,
            'Email': user.email,
            'Adv Source': user.adv_source,
            'Gems Total': user.gems_total,
            'Spins Total': user.spins_total,
            'Spins Left': user.spins_left,
            'Spins Limit': user.spins_limit,
            'Tournament Wins': user.tournament_wins,
            'Demo Clicks': user.demo_clicks,
            'Is Muted': user.is_muted,
            'Is Banned': user.is_banned,
            'Last Spin Time': user.last_spin_time.strftime('%Y-%m-%d %H:%M:%S') if user.last_spin_time else '-',
            'Next Refill Time': user.next_refill_time.strftime('%Y-%m-%d %H:%M:%S') if user.next_refill_time else '-'
        })

    update_google_sheet(USERS_SHEET_NAME, 'ID', rows)
