from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.link import create_telegram_link

from src import database
from src.config import BOT_USERNAME, AVAILABLE_LANGUAGES, SERVER_DOMAIN
from src.models import User
from src.translations import _


def create_start_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text=_("start", language),
            callback_data=f"select_language_{language}"
        )] for language in AVAILABLE_LANGUAGES]
    )


def create_iguild_keyboard(user: User):
    keyboard_buttons = [
        [InlineKeyboardButton(text=_("weekly_challenge", user.language), callback_data="weekly_challenge")],
        [InlineKeyboardButton(text=_("bonus", user.language), callback_data="bonus")],
        [InlineKeyboardButton(text=_("referral", user.language), callback_data="referral")],
        [InlineKeyboardButton(text=_("start", user.language), callback_data="start")]
    ]

    if not user.is_muted:
        keyboard_buttons.insert(1, [InlineKeyboardButton(text=_("anon_chat", user.language), callback_data="anon_chat")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def create_weekly_challenge_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("winning_schemes", language), callback_data="winning_schemes")],
            [InlineKeyboardButton(text=_("leaderboard", language), callback_data="leaderboard")],
            # [InlineKeyboardButton(text=_("igaming_pass", language), callback_data="igaming_pass")],
            [InlineKeyboardButton(text=_("iguild", language), callback_data="iguild")]
        ]
    )


def create_winning_schemes_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("leaderboard", language), callback_data="leaderboard")],
            # [InlineKeyboardButton(text=_("igaming_pass", language), callback_data="igaming_pass")],
            [InlineKeyboardButton(text=_("iguild", language), callback_data="iguild")],
            [InlineKeyboardButton(text=_("weekly_challenge", language), callback_data="weekly_challenge")]
        ]
    )


def create_leaderboard_keyboard(language: str):
    keyboard_buttons = [
        # [InlineKeyboardButton(text=_("igaming_pass", language), callback_data="igaming_pass")],
        [InlineKeyboardButton(text=_("iguild", language), callback_data="iguild")],
        [InlineKeyboardButton(text=_("weekly_challenge", language), callback_data="weekly_challenge")],
        [InlineKeyboardButton(text=_("winning_schemes", language), callback_data="winning_schemes")]
    ]

    if database.get_current_tournament():
        keyboard_buttons.insert(0, [
            InlineKeyboardButton(text=_("leaderboard_weekly", language), callback_data="leaderboard_weekly"),
            InlineKeyboardButton(text=_("leaderboard_all_time_active", language), callback_data="leaderboard_all_time")
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def create_weekly_leaderboard_keyboard(language: str):
    keyboard_buttons = [
        # [InlineKeyboardButton(text=_("igaming_pass", language), callback_data="igaming_pass")],
        [InlineKeyboardButton(text=_("iguild", language), callback_data="iguild")],
        [InlineKeyboardButton(text=_("weekly_challenge", language), callback_data="weekly_challenge")],
        [InlineKeyboardButton(text=_("winning_schemes", language), callback_data="winning_schemes")]
    ]

    if database.get_current_tournament():
        keyboard_buttons.insert(0, [
            InlineKeyboardButton(text=_("leaderboard_weekly_active", language), callback_data="leaderboard_weekly"),
            InlineKeyboardButton(text=_("leaderboard_all_time", language), callback_data="leaderboard_all_time")
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def create_igaming_pass_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("iguild", language), callback_data="iguild")],
            [InlineKeyboardButton(text=_("weekly_challenge", language), callback_data="weekly_challenge")],
            [InlineKeyboardButton(text=_("winning_schemes", language), callback_data="winning_schemes")],
            [InlineKeyboardButton(text=_("leaderboard", language), callback_data="leaderboard")]
        ]
    )


def create_referral_keyboard(user: User, inline_message_id: str):
    keyboard_buttons = [
        [InlineKeyboardButton(text=_("share", user.language), web_app=WebAppInfo(url=f"https://{SERVER_DOMAIN}/share?inline_message_id={inline_message_id}"))],
        [InlineKeyboardButton(text=_("bonus", user.language), callback_data="bonus")],
        [InlineKeyboardButton(text=_("iguild", user.language), callback_data="iguild")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def create_bonus_keyboard(user: User):
    keyboard_buttons = [
        [InlineKeyboardButton(text=_("check_bonus", user.language), callback_data="bonus")],
        [InlineKeyboardButton(text=_("iguild", user.language), callback_data="iguild")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def create_anon_chat_keyboard(user: User):
    keyboard_buttons = [
        [InlineKeyboardButton(text=_("update_name", user.language), callback_data="update_name")],
        [InlineKeyboardButton(text=_("iguild", user.language), callback_data="iguild")]
    ]

    if not user.is_muted:
        keyboard_buttons.insert(1, [InlineKeyboardButton(text=_("anon_chat_start", user.language), callback_data="anon_chat_start")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def create_back_iguild_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("iguild", language), callback_data="iguild")],
        ]
    )


def create_back_leaderboard_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("leaderboard", language), callback_data="leaderboard")]
        ]
    )


def create_back_anon_chat_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("cancel", language), callback_data="anon_chat")]
        ]
    )


def create_anon_chat_send_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("send", language), callback_data="send")],
            [InlineKeyboardButton(text=_("cancel", language), callback_data="anon_chat_start")]
        ]
    )


def create_no_spins_left_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("leaderboard", language), callback_data="leaderboard")],
            [InlineKeyboardButton(text=_("claim_bonus", language), url=create_telegram_link(BOT_USERNAME, "app"))]
        ]
    )


def create_message_sent_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("anon_chat", language), callback_data="anon_chat")],
            [InlineKeyboardButton(text=_("iguild", language), callback_data="iguild")]
        ]
    )


def create_play_keyboard(language: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_("play", language))],
        ],
        resize_keyboard=True
    )


def create_play_group_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("play"), url=create_telegram_link(BOT_USERNAME))]
        ]
    )


def create_send_email_keyboard(language: str, tournament_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("send_email", language), callback_data=f"send_email_{tournament_id}")]
        ]
    )


def create_tournament_keyboard(language: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("weekly_challenge", language), callback_data="weekly_challenge")],
            [InlineKeyboardButton(text=_("bonus", language), callback_data="bonus")],
            [InlineKeyboardButton(text=_("start", language), callback_data="start")]
        ]
    )


def create_user_info_keyboard(user: User, target: User):
    keyboard_buttons = [[InlineKeyboardButton(text=_("leaderboard", user.language), callback_data="leaderboard")]]

    if user.is_admin and not target.is_admin and not target.is_fake:
        keyboard_buttons.append([InlineKeyboardButton(text=_("mute" if not target.is_muted else "unmute", user.language), callback_data=f"mute_{target.id}")])
        keyboard_buttons.append([InlineKeyboardButton(text=_("ban" if not target.is_banned else "unban", user.language), callback_data=f"ban_{target.id}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
