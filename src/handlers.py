import random
import uuid
from contextlib import suppress
from datetime import datetime

from aiogram import Bot, F
from aiogram import Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatType
from aiogram.filters import Command, CommandObject
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, LinkPreviewOptions, InlineQueryResultPhoto, InlineQuery
from aiogram.types import Message
from async_lru import alru_cache

from src import translations
from src.config import BOT_TOKEN, SPIN_REWARDS, MAIN_GROUP_ID, WIN_EMOJIS, GAME_TOPIC_ID, FEEDBACK_TOPIC_ID, WINNERS_SHEET_NAME, FEEDBACK_TOPIC_URL, DEFAULT_SPINS_AMOUNT, MAIN_GROUP_URL, BONUS_CHANNELS
from src.images import get_referral_image
from src.keyboards import *
from src.models import User
from src.sheets import add_to_google_sheet
from src.states import AnonChatState, SendEmailState, ClearStateMiddleware
from src.translations import _
from src.utils import get_spin_result, format_spin_result, get_spin_win_text, is_valid_email, format_tournament_info, format_refill_time_info, format_admin_user_info, format_next_refill_time, generate_random_name, format_channels_info

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True, link_preview_show_above_text=True, show_caption_above_media=False))
router = Router()

router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)

router.message.filter(F.from_user.func(lambda user: not database.is_user_banned(user.id)))
router.callback_query.filter(F.from_user.func(lambda user: not database.is_user_banned(user.id)))

router.message.middleware(ClearStateMiddleware())
router.callback_query.middleware(ClearStateMiddleware())


@router.message(CommandStart())
async def start_command(message: Message, command: CommandObject):
    user = database.get_user(message.from_user.id)
    if not user:
        adv_source, referrer_id = None, None

        if command.args:
            if command.args.startswith('a'):
                adv_source = command.args[1:]
            elif command.args.startswith('r'):
                referrer_id = int(command.args[1:])

        referrer = database.get_user_by_id(referrer_id) if referrer_id else None
        if referrer:
            referrer.spins_left += DEFAULT_SPINS_AMOUNT
            database.commit()

            await send_message(referrer.chat_id, _("spins_refilled_referral", referrer.language))

        user = User(
            chat_id=message.from_user.id,
            username=message.from_user.username or message.from_user.full_name,
            language=message.from_user.language_code,
            adv_source=adv_source,
            referrer_id=referrer_id if referrer else None
        )
        database.add_user(user)

    if command.args and command.args.startswith('u'):
        target = database.get_user_by_id(int(command.args[1:]))
        if target:
            await send_user_info_message(message, user, target)
            return

    await send_start_message(message)


@router.message(Command("iguild"))
async def iguild_command(message: Message):
    user = database.get_user(message.from_user.id)
    if user:
        await send_iguild_message(message, user)


@router.message(Command("reset"))
async def reset_command(message: Message, state: FSMContext):
    await state.clear()
    await send_start_message(message)


@router.message(Command("pass"))
async def pass_command(message: Message):
    user = database.get_user(message.from_user.id)
    if user:
        await send_igaming_pass_message(message, user)


@router.message(Command("ref"))
async def ref_command(message: Message):
    user = database.get_user(message.from_user.id)
    if user:
        await send_referral_message(message, user)


@router.message(Command("bonus"))
async def ref_command(message: Message):
    user = database.get_user(message.from_user.id)
    if user:
        await send_bonus_message(message, user)


@router.message(Command("anon"))
async def anon_command(message: Message, state: FSMContext):
    user = database.get_user(message.from_user.id)
    if not user:
        return

    if user.is_muted:
        await message.answer(_("mute_info", user.language))
        return

    await state.set_state(AnonChatState.message)
    await send_anon_chat_start_message(message, user)


@router.message(Command("spin"))
async def spin_command(message: Message):
    user = database.get_user(message.from_user.id)
    if user and await check_can_spin(message, user):
        spin_message = await message.answer_dice("🎰", reply_markup=create_play_keyboard(user.language))
        await handle_spin_result(spin_message, user)


@router.callback_query(F.data.startswith("select_language_"))
async def select_language_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        user.language = callback.data[len('select_language_'):]
        database.commit()

        await send_iguild_message(callback.message, user)


@router.callback_query(F.data == "start")
async def start_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        await send_start_message(callback.message)


@router.callback_query(F.data == "iguild")
async def iguild_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        await send_iguild_message(callback.message, user)


@router.callback_query(F.data == "weekly_challenge")
async def weekly_challenge_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        await send_weekly_challenge_message(callback.message, user)


@router.callback_query(F.data == "winning_schemes")
async def winning_schemes_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        await send_winning_schemes_message(callback.message, user)


@router.callback_query(F.data == "leaderboard")
async def leaderboard_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if not user:
        return

    current_tournament = database.get_current_tournament()
    if not current_tournament:
        await send_leaderboard_message(callback.message, user)
    else:
        await send_leaderboard_weekly_message(callback.message, user)


@router.callback_query(F.data == "leaderboard_all_time")
async def leaderboard_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        await send_leaderboard_message(callback.message, user, edit_original=True)


@router.callback_query(F.data == "leaderboard_weekly")
async def leaderboard_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        await send_leaderboard_weekly_message(callback.message, user, edit_original=True)


@router.callback_query(F.data == "igaming_pass")
async def igaming_pass_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        await send_igaming_pass_message(callback.message, user)


@router.callback_query(F.data == "play")
async def play_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user and await check_can_spin(callback.message, user):
        spin_message = await callback.message.answer_dice("🎰", reply_markup=create_play_keyboard(user.language))
        await handle_spin_result(spin_message, user)


@router.callback_query(F.data == "referral")
async def referral_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        await send_referral_message(callback.message, user)


@router.callback_query(F.data == "bonus")
async def bonus_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        await send_bonus_message(callback.message, user)


@router.callback_query(F.data == "anon_chat")
async def anon_chat_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        await send_anon_chat_message(callback.message, user)


@router.callback_query(F.data == "update_name")
async def update_name_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if user:
        user.anon_name = generate_random_name()
        database.commit()

        await send_anon_chat_message(callback.message, user)


@router.callback_query(F.data == "anon_chat_start")
async def anon_chat_start_callback(callback: CallbackQuery, state: FSMContext):
    user = database.get_user(callback.from_user.id)
    if not user or user.is_muted:
        return

    await state.set_state(AnonChatState.message)
    await send_anon_chat_start_message(callback.message, user)


@router.callback_query(F.data.startswith("send_email_"))
async def send_email_callback(callback: CallbackQuery, state: FSMContext):
    user = database.get_user(callback.from_user.id)
    if not user:
        return

    tournament = database.get_tournament(callback.data[len('send_email_'):])
    if not tournament:
        return

    tournament_stats = database.get_user_tournament_stats(user.id, tournament.id)
    if tournament_stats.is_email_sent:
        await callback.message.answer(_("send_email_already_sent", user.language), reply_markup=create_back_iguild_keyboard(user.language))
        return

    await state.set_state(SendEmailState.email)
    await state.update_data(tournament_id=tournament.id)
    await send_send_email_message(callback.message, user)


@router.callback_query(F.data.startswith("mute_"))
async def mute_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if not user or not user.is_admin:
        return

    target = database.get_user_by_id(callback.data[len("mute_"):])
    if not target or target.is_admin or target.is_fake:
        await callback.message.answer_or_edit(_("mute_invalid_target", user.language))
        return

    target.is_muted = not target.is_muted
    database.commit()

    await send_message(target.chat_id, _("mute_info" if target.is_muted else "unmute_info", target.language))
    await callback.message.answer_or_edit(_("mute_success" if target.is_muted else "unmute_success", user.language, anon_name=target.mention_anon_name()), reply_markup=create_back_iguild_keyboard(user.language))


@router.callback_query(F.data.startswith("ban_"))
async def ban_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if not user or not user.is_admin:
        return

    target = database.get_user_by_id(callback.data[len("ban_"):])
    if not target or target.is_admin or target.is_fake:
        await callback.message.answer_or_edit(_("ban_invalid_target", user.language))
        return

    target.is_banned = not target.is_banned
    database.commit()

    if target.is_banned:
        await bot.send_message(target.chat_id, _("ban_info", target.language))
        await bot.ban_chat_member(MAIN_GROUP_ID, target.chat_id)
    else:
        await bot.send_message(target.chat_id, _("unban_info", target.language))
        await bot.unban_chat_member(MAIN_GROUP_ID, target.chat_id)

    await callback.message.answer_or_edit(_("ban_success" if target.is_banned else "unban_success", user.language, anon_name=target.mention_anon_name()), reply_markup=create_back_iguild_keyboard(user.language))


@router.message(F.text.in_(translations.get_all_translations("play")))
async def play_message_handler(message: Message):
    user = database.get_user(message.from_user.id)
    if user and await check_can_spin(message, user):
        spin_message = await message.answer_dice("🎰")
        await handle_spin_result(spin_message, user)


@router.message(F.dice.emoji == "🎰")
async def slots_dice_handler(message: Message):
    user = database.get_user(message.from_user.id)
    if user and await check_can_spin(message, user):
        await handle_spin_result(message, user)


@router.message(AnonChatState.message)
async def anon_chat_message_handler(message: Message):
    user = database.get_user(message.from_user.id)
    if not user or user.is_muted:
        return

    quoted_text = _("forwarded_from_text" if message.html_text else "forwarded_from",
                    anon_name=user.format_anon_name(),
                    message_text=message.html_text)

    if message.photo:
        await message.answer_photo(message.photo[-1].file_id, caption=quoted_text, reply_markup=create_anon_chat_send_keyboard(user.language))

    elif message.video:
        await message.answer_video(message.video.file_id, caption=quoted_text, reply_markup=create_anon_chat_send_keyboard(user.language))

    elif message.audio:
        await message.answer_audio(message.audio.file_id, caption=quoted_text, reply_markup=create_anon_chat_send_keyboard(user.language))

    elif message.animation:
        await message.answer_animation(message.animation.file_id, caption=quoted_text, reply_markup=create_anon_chat_send_keyboard(user.language))

    elif message.sticker:
        sticker_message = await message.answer_sticker(message.sticker.file_id)
        await sticker_message.reply(quoted_text, reply_markup=create_anon_chat_send_keyboard(user.language))

    elif message.text:
        await message.answer(quoted_text, reply_markup=create_anon_chat_send_keyboard(user.language))


@router.callback_query(F.data == "send")
async def send_callback(callback: CallbackQuery):
    user = database.get_user(callback.from_user.id)
    if not user or user.is_muted:
        return

    if callback.message.photo:
        sent_message = await bot.send_photo(MAIN_GROUP_ID, callback.message.photo[-1].file_id, caption=callback.message.html_text, message_thread_id=FEEDBACK_TOPIC_ID)

    elif callback.message.video:
        sent_message = await bot.send_video(MAIN_GROUP_ID, callback.message.video.file_id, caption=callback.message.html_text, message_thread_id=FEEDBACK_TOPIC_ID)

    elif callback.message.audio:
        sent_message = await bot.send_audio(MAIN_GROUP_ID, callback.message.audio.file_id, caption=callback.message.html_text, message_thread_id=FEEDBACK_TOPIC_ID)

    elif callback.message.animation:
        sent_message = await bot.send_animation(MAIN_GROUP_ID, callback.message.animation.file_id, caption=callback.message.html_text, message_thread_id=FEEDBACK_TOPIC_ID)

    elif callback.message.reply_to_message and callback.message.reply_to_message.sticker:
        sticker_message = await bot.send_sticker(MAIN_GROUP_ID, callback.message.reply_to_message.sticker.file_id, message_thread_id=FEEDBACK_TOPIC_ID)
        sent_message = await sticker_message.reply(callback.message.html_text)

    else:
        sent_message = await bot.send_message(MAIN_GROUP_ID, callback.message.html_text, message_thread_id=FEEDBACK_TOPIC_ID)

    await send_message_sent_message(callback.message, sent_message, user)


@router.message(SendEmailState.email)
async def send_email_message_handler(message: Message, state: FSMContext):
    user = database.get_user(message.from_user.id)
    if not user:
        return

    if not is_valid_email(message.text):
        await message.answer(_("send_email_error", user.language), reply_markup=create_back_iguild_keyboard(user.language))
        await state.clear()
        return

    data = await state.get_data()
    tournament = database.get_tournament(data["tournament_id"])

    tournament_stats = database.get_user_tournament_stats(user.id, tournament.id)
    tournament_stats.is_email_sent = True

    user.email = message.text
    database.commit()

    data = {
        'Username': user.username,
        'ID': user.chat_id,
        'Anon Name': user.anon_name,
        'Email': user.email,
        'Tournament Date': tournament.end_date.strftime('%Y/%m/%d'),
        'Email Sent Date': datetime.utcnow().strftime('%Y/%m/%d'),
        'Total Gems': user.gems_total,
        'Tournament Gems': tournament_stats.gems
    }

    if not add_to_google_sheet(WINNERS_SHEET_NAME, data):
        await message.answer(_("send_email_error", user.language), reply_markup=create_back_iguild_keyboard(user.language))
        await state.clear()
        return

    await message.answer(_("send_email_sent", user.language), reply_markup=create_back_iguild_keyboard(user.language))
    await state.clear()


@router.inline_query()
async def share_results_inline_query(inline: InlineQuery):
    user = database.get_user(inline.from_user.id)
    if not user:
        return

    await inline.answer(
        [
            InlineQueryResultPhoto(
                id=str(uuid.uuid4()),
                photo_url=f"https://{SERVER_DOMAIN}/results?user_id={user.chat_id}",
                thumbnail_url=f"https://{SERVER_DOMAIN}/results?user_id={user.chat_id}",
                caption=_("referral_message", user.language, referral_link=user.create_referral_link())
            )
        ],
        cache_time=30
    )


async def send_start_message(message: Message):
    await message.answer_or_edit(
        _("pick_language", message.from_user.language_code),
        reply_markup=create_start_keyboard()
    )


async def send_iguild_message(message: Message, user: User):
    await message.answer_or_edit(
        _("iguild_info", user.language, username=user.mention_username(), anon_name=user.format_anon_name(), group_url=MAIN_GROUP_URL),
        image_path="assets/images/igaming_community.png",
        reply_markup=create_iguild_keyboard(user)
    )


async def send_weekly_challenge_message(message: Message, user: User):
    await message.answer_or_edit(
        _("weekly_challenge_info", user.language, group_url=MAIN_GROUP_URL),
        reply_markup=create_weekly_challenge_keyboard(user.language),
        link_preview_options=LinkPreviewOptions(is_disabled=False)
    )


async def send_winning_schemes_message(message: Message, user: User):
    await message.answer_or_edit(
        _("winning_schemes_info", user.language),
        reply_markup=create_winning_schemes_keyboard(user.language)
    )


async def send_leaderboard_message(message: Message, user: User, edit_original=False):
    leaderboard = database.get_leaderboard()
    leaderboard_text = ""

    for leader in leaderboard:
        if leader == user:
            leaderboard_text += f"<b>{leader.gems_total} 💎 {leader.format_anon_name(with_icon=False)}</b> 🥷\n"
        else:
            leaderboard_text += f"{leader.gems_total} 💎 {leader.format_anon_name(with_icon=False)}\n"

    if user not in leaderboard:
        if leaderboard:
            leaderboard_text += "<b>***</b>\n"
        leaderboard_text += f"<b>{user.gems_total} 💎 {user.format_anon_name(with_icon=False)}</b> 🥷\n"

    await message.answer_or_edit(
        _("leaderboard_info", user.language,
          anon_name=user.format_anon_name(),
          gems_total=user.gems_total,
          spins_total=user.spins_total,
          gems_referral=user.gems_referral,
          tournament_wins=user.tournament_wins,
          tournament_king_wins=user.max_tournament_king_wins,
          leaderboard_text=leaderboard_text),
        reply_markup=create_leaderboard_keyboard(user.language),
        edit_original=edit_original
    )


async def send_leaderboard_weekly_message(message: Message, user: User, edit_original=False):
    current_tournament = database.get_current_tournament()
    if not current_tournament:
        return

    leaderboard = database.get_tournament_leaderboard(current_tournament.id)
    leaderboard_text = ""

    for stats in leaderboard:
        if stats.user == user:
            leaderboard_text += f"<b>{stats.gems} 💎 {stats.user.format_anon_name(with_icon=False)}</b> 🥷\n"
        else:
            leaderboard_text += f"{stats.gems} 💎 {stats.user.format_anon_name(with_icon=False)}\n"

    current_tournament_stats = database.get_user_tournament_stats(user.id, current_tournament.id)
    if current_tournament_stats not in leaderboard:
        if leaderboard:
            leaderboard_text += "<b>***</b>\n"
        leaderboard_text += f"<b>{current_tournament_stats.gems} 💎 {user.format_anon_name(with_icon=False)}</b> 🥷\n"

    await message.answer_or_edit(
        _("leaderboard_info_weekly", user.language,
          anon_name=user.format_anon_name(),
          current_tournament_gems=current_tournament_stats.gems,
          current_tournament_spins=current_tournament_stats.spins,
          spins_left=user.spins_left,
          spins_limit=await get_bonus_spins_limit(user),
          refill_time_info=format_refill_time_info(user),
          leaderboard_text=leaderboard_text),
        reply_markup=create_weekly_leaderboard_keyboard(user.language),
        edit_original=edit_original
    )


async def send_user_info_message(message: Message, user: User, target: User):
    current_tournament = database.get_current_tournament()
    current_tournament_stats = database.get_user_tournament_stats(target.id, current_tournament.id) if current_tournament else None

    await message.answer(
        _("user_info", user.language,
          anon_name=target.format_anon_name(),
          gems_total=target.gems_total,
          spins_total=target.spins_total,
          tournament_info=format_tournament_info(user, current_tournament_stats),
          admin_user_info=format_admin_user_info(user, target),
          tournament_wins=target.tournament_wins,
          tournament_king_wins=target.max_tournament_king_wins),
        reply_markup=create_user_info_keyboard(user, target)
    )


async def send_igaming_pass_message(message: Message, user: User):
    await message.answer_or_edit(
        _("igaming_pass_info", user.language),
        image_path="assets/images/iguild_nft_pass.png",
        reply_markup=create_igaming_pass_keyboard(user.language)
    )


async def send_referral_message(message: Message, user: User):
    referrals = sorted(user.referrals, key=lambda referral: referral.gems_total, reverse=True)
    referrals_text = ""

    for referral in referrals[:10]:
        referrals_text += f"{referral.gems_total} 💎 {referral.format_anon_name(with_icon=False)}\n"

    inline_message = await bot.save_prepared_inline_message(
        message.from_user.id,
        InlineQueryResultPhoto(
            id=str(uuid.uuid4()),
            photo_url=f"https://{SERVER_DOMAIN}/results?user_id={user.chat_id}",
            thumbnail_url=f"https://{SERVER_DOMAIN}/results?user_id={user.chat_id}",
            caption=_("referral_message", user.language, referral_link=user.create_referral_link())
        ),
        allow_user_chats=True,
        allow_group_chats=True,
        allow_channel_chats=True
    )

    await message.answer_or_edit(
        _("referral_info", user.language,
          referral_link=user.create_referral_link(),
          referrals_shown=min(len(referrals), 10),
          referrals_total=len(referrals),
          referrals_text=referrals_text),
        image_path=get_referral_image(user),
        reply_markup=create_referral_keyboard(user, inline_message.id)
    )


async def send_bonus_message(message: Message, user: User):
    channels = [
        {**channel, 'subscribed': await is_subscribed(user, channel['id'])}
        for channel in BONUS_CHANNELS
    ]

    await message.answer_or_edit(
        _("bonus_info", user.language,
          channels_info=format_channels_info(user, channels),
          spins_left=user.spins_left,
          spins_limit=await get_bonus_spins_limit(user),
          refill_time_info=format_refill_time_info(user)),
        image_path="assets/images/complete_tasks.png",
        reply_markup=create_bonus_keyboard(user)
    )


async def send_anon_chat_message(message: Message, user: User):
    await message.answer_or_edit(
        _("anon_chat_info", user.language,
          username=user.mention_username(),
          anon_name=user.format_anon_name()),
        reply_markup=create_anon_chat_keyboard(user)
    )


async def send_anon_chat_start_message(message: Message, user: User):
    await message.answer_or_edit(
        _("anon_chat_start_info", user.language,
          group_url=MAIN_GROUP_URL,
          feedback_topic_url=FEEDBACK_TOPIC_URL),
        reply_markup=create_back_anon_chat_keyboard(user.language)
    )


async def send_message_sent_message(message: Message, sent_message: Message, user: User):
    await message.answer_or_edit(
        _("anon_chat_message_sent", user.language, message_url=sent_message.get_url()),
        reply_markup=create_message_sent_keyboard(user.language)
    )


async def send_send_email_message(message: Message, user: User):
    await message.answer_or_edit(_("send_email_info", user.language), image_path="assets/images/add_your_email.png", delete_original=False)


async def check_can_spin(message: Message, user: User):
    if user.spins_left > 0:
        database.record_user_spin(user)
        return True

    current_tournament = database.get_current_tournament()
    current_tournament_stats = database.get_user_tournament_stats(user.id, current_tournament.id) if current_tournament else None

    await message.answer(_("no_spins_left", user.language, next_refill_time=format_next_refill_time(user), tournament_info=format_tournament_info(user, current_tournament_stats)), reply_markup=create_no_spins_left_keyboard(user.language))
    return False


async def handle_spin_result(message: Message, user: User):
    spin_result = get_spin_result(message.dice.value)
    spin_reward = SPIN_REWARDS.get(spin_result, 0)

    database.credit_user_spin_reward(user, spin_reward, spin_result == "777")

    current_tournament = database.get_current_tournament()
    current_tournament_stats = database.get_user_tournament_stats(user.id, current_tournament.id) if current_tournament else None

    if spin_reward:
        await message.answer(
            _("spin_win", user.language,
              random_text=get_spin_win_text(spin_result, user.language),
              spin_result=format_spin_result(spin_result),
              spin_reward=spin_reward,
              gems_total=current_tournament_stats.gems if current_tournament_stats else user.gems_total,
              spins_left=user.spins_left)
        )

        if len(spin_result) == 3 or (len(spin_result) == 2 and random.random() <= 0.2):
            if len(spin_result) == 3:
                await send_group_message(GAME_TOPIC_ID, random.choice(WIN_EMOJIS))

            await send_group_message(
                GAME_TOPIC_ID,
                _("spin_win_group",
                  random_text=get_spin_win_text(spin_result),
                  spin_result=format_spin_result(spin_result),
                  spin_reward=spin_reward,
                  anon_name=user.format_anon_name())
            )

    else:
        await message.answer(
            _("spin_lose", user.language,
              gems_total=current_tournament_stats.gems if current_tournament_stats else user.gems_total,
              spins_left=user.spins_left)
        )


@alru_cache(ttl=5)
async def is_subscribed(user: User, channel_id: int) -> bool:
    with suppress(Exception):
        chat_member = await bot.get_chat_member(channel_id, user.chat_id)
        return chat_member.status not in {'left', 'kicked'}


async def get_subscription_spins_bonus(user: User) -> int:
    total_spins = 0
    for channel in BONUS_CHANNELS:
        if await is_subscribed(user, channel['id']):
            total_spins += DEFAULT_SPINS_AMOUNT
    return total_spins


async def get_bonus_spins_limit(user: User) -> int:
    referral_spins_bonus = database.get_referral_spins_bonus(user)
    subscription_bonus = await get_subscription_spins_bonus(user)

    return user.spins_limit + referral_spins_bonus + subscription_bonus


uploaded_photos = {}


def get_uploaded_photo(image_path: str) -> str | FSInputFile:
    return uploaded_photos.get(image_path, FSInputFile(image_path))


def set_uploaded_photo(image_path, file_id):
    uploaded_photos[image_path] = file_id


async def answer_or_edit(message: Message, text: str, image_path: str = None, edit_original: bool = False, delete_original: bool = True, **kwargs):
    if image_path:
        sent_message = await message.answer_photo(get_uploaded_photo(image_path), caption=text, **kwargs)
        set_uploaded_photo(image_path, sent_message.photo[-1].file_id)
    elif edit_original:
        await message.edit_text(text, **kwargs)
    else:
        await message.answer(text, **kwargs)

    if not edit_original and delete_original and message.from_user.is_bot:
        with suppress(Exception):
            await message.delete()


Message.answer_or_edit = answer_or_edit


async def send_group_message(topic_id: int, text: str, image_path: str = None, **kwargs) -> Message:
    if image_path:
        sent_message = await bot.send_photo(MAIN_GROUP_ID, get_uploaded_photo(image_path), caption=text, message_thread_id=topic_id, **kwargs)
        set_uploaded_photo(image_path, sent_message.photo[-1].file_id)

        return sent_message
    else:
        return await bot.send_message(MAIN_GROUP_ID, text, message_thread_id=topic_id, **kwargs)


async def send_message(chat_id: int, text: str, **kwargs) -> Message | None:
    with suppress(Exception):
        return await bot.send_message(chat_id, text, **kwargs)


async def delete_message(chat_id: int, message_id: int) -> bool | None:
    with suppress(Exception):
        return await bot.delete_message(chat_id, message_id)
