import math
from datetime import date, timedelta, datetime

from sqlalchemy import create_engine
from sqlalchemy import update
from sqlalchemy.orm import sessionmaker

from src.config import DATABASE_URL, SPIN_REFILL_DELAY, REFERRAL_GEMS_RATE, DEFAULT_SPINS_AMOUNT, FAKE_USERS_AMOUNT
from src.models import Base, User, Tournament, UserTournamentStats

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


def commit():
    session.commit()


def add_user(user: User):
    session.add(user)
    commit()


def get_user(chat_id: int) -> User:
    return session.query(User).filter_by(chat_id=chat_id).first()  # type: ignore


def get_user_by_id(user_id: int) -> User:
    return session.get(User, user_id)  # type: ignore


def get_user_by_chat_id(chat_id: int) -> User:
    return session.query(User).filter_by(chat_id=chat_id).first()  # type: ignore


def get_all_users(**kwargs) -> list:
    return session.query(User).filter_by(**kwargs).all()


def get_leaderboard() -> list:
    return session.query(User).filter(User.gems_total > 0).order_by(User.gems_total.desc()).limit(10).all()


def is_user_banned(chat_id: int) -> bool:
    user = get_user(chat_id)
    return user.is_banned if user else False


def reset_spins_for_all_users(spins_amount):
    session.execute(update(User).values(spins_limit=spins_amount, spins_left=spins_amount))
    commit()


def record_user_spin(user: User):
    user.spins_total += 1
    user.spins_left -= 1
    user.warning_level = 0
    user.last_spin_time = datetime.utcnow()

    if not user.next_refill_time:
        user.next_refill_time = datetime.utcnow() + timedelta(hours=SPIN_REFILL_DELAY)

    current_tournament = get_current_tournament()
    if current_tournament:
        current_tournament_stats = get_user_tournament_stats(user.id, current_tournament.id)
        current_tournament_stats.spins += 1

    commit()


def credit_user_spin_reward(user: User, spin_reward: int, is_jackpot: bool):
    user.gems_total += spin_reward
    if is_jackpot:
        user.jackpots_total += 1

    current_tournament = get_current_tournament()
    if current_tournament:
        current_tournament_stats = get_user_tournament_stats(user.id, current_tournament.id)
        current_tournament_stats.gems += spin_reward
        if is_jackpot:
            current_tournament_stats.jackpots += 1

    if user.referrer:
        user.referrer.gems_total += math.ceil(spin_reward * REFERRAL_GEMS_RATE)
        user.referrer.gems_referral += math.ceil(spin_reward * REFERRAL_GEMS_RATE)

        if current_tournament:
            referrer_tournament_stats = get_user_tournament_stats(user.referrer_id, current_tournament.id)
            referrer_tournament_stats.gems += math.ceil(spin_reward * REFERRAL_GEMS_RATE)

    commit()


def get_referral_spins_bonus(user: User) -> int:
    current_tournament = get_current_tournament()
    if not current_tournament:
        return 0

    return sum(
        DEFAULT_SPINS_AMOUNT
        for referral in user.referrals
        if get_user_tournament_stats(referral.id, current_tournament.id).spins > 0
    )


def start_new_tournament() -> Tournament:
    current_tournament = get_current_tournament()
    if current_tournament:
        return current_tournament

    start_date = date.today() - timedelta(days=date.today().weekday())
    end_date = start_date + timedelta(days=6)

    new_tournament = Tournament(start_date=start_date, end_date=end_date, is_active=True)
    session.add(new_tournament)
    commit()

    return new_tournament


def get_tournament(tournament_id: int) -> Tournament:
    return session.get(Tournament, tournament_id)  # type: ignore


def get_current_tournament() -> Tournament:
    return session.query(Tournament).filter_by(is_active=True).first()  # type: ignore


def end_current_tournament() -> Tournament:
    current_tournament = get_current_tournament()
    if current_tournament:
        current_tournament.is_active = False
        commit()

    return current_tournament


def get_tournament_leaderboard(tournament_id: int) -> list:
    return session.query(UserTournamentStats).filter_by(tournament_id=tournament_id).filter(UserTournamentStats.gems > 0).order_by(UserTournamentStats.gems.desc()).limit(10).all()


def get_user_tournament_stats(user_id: int, tournament_id: int) -> UserTournamentStats:
    stats = session.query(UserTournamentStats).filter_by(user_id=user_id, tournament_id=tournament_id).first()

    if not stats:
        stats = UserTournamentStats(user_id=user_id, tournament_id=tournament_id)
        session.add(stats)
        commit()

    return stats


def create_fake_users(amount):
    session.bulk_save_objects([User(username="Bot", is_fake=True) for _ in range(amount)])
    commit()


if not session.query(User).first():
    create_fake_users(FAKE_USERS_AMOUNT)
