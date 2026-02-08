from datetime import datetime

from aiogram.utils import markdown
from aiogram.utils.deep_linking import create_deep_link
from aiogram.utils.link import create_tg_link
from sqlalchemy import Column, BigInteger, Integer, DateTime, ForeignKey, String, Boolean, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

from src.config import DEFAULT_SPINS_AMOUNT, BOT_ADMINS, BOT_USERNAME
from src.utils import generate_random_name, get_random_time_this_hour

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False, default=0)
    username = Column(String, nullable=False)
    language = Column(String, nullable=False, default='en')
    created_at = Column(DateTime, default=datetime.utcnow)
    anon_name = Column(String, nullable=False, default=generate_random_name)
    email = Column(String, default=None)
    adv_source = Column(String, default=None)

    gems_total = Column(Integer, default=0)
    gems_referral = Column(Integer, default=0)
    spins_total = Column(Integer, default=0)
    spins_left = Column(Integer, default=DEFAULT_SPINS_AMOUNT)
    spins_limit = Column(Integer, default=DEFAULT_SPINS_AMOUNT)
    jackpots_total = Column(Integer, default=0)
    tournament_wins = Column(Integer, default=0)
    tournament_king_wins = Column(Integer, default=0)
    max_tournament_king_wins = Column(Integer, default=0)
    demo_clicks = Column(Integer, default=0)
    warning_level = Column(Integer, default=0)
    last_warning_message_id = Column(Integer, default=0)

    is_fake = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    is_muted = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    is_previous_tournament_winner = Column(Boolean, default=False)

    last_spin_time = Column(DateTime, default=None)
    next_refill_time = Column(DateTime, default=None)
    next_autospin_time = Column(DateTime, default=get_random_time_this_hour)

    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referrals = relationship('User', backref=backref('referrer', remote_side=[id]), cascade='all')

    tournament_stats = relationship('UserTournamentStats', back_populates='user', cascade='all, delete-orphan')

    @property
    def is_admin(self):
        return self.chat_id in BOT_ADMINS

    def create_user_link(self):
        return create_tg_link('user', id=self.chat_id)

    def create_info_link(self):
        return create_deep_link(BOT_USERNAME, 'start', f'u{self.id}')

    def create_referral_link(self):
        return create_deep_link(BOT_USERNAME, 'start', f'r{self.id}')

    def mention_username(self):
        if self.is_fake:
            return f'Bot #{self.id}'
        return markdown.hlink(self.username, self.create_user_link())  # type: ignore

    def mention_anon_name(self):
        return markdown.hlink(self.anon_name, self.create_info_link())  # type: ignore

    def format_anon_name(self, with_icon: bool = True):
        icon = '👑' if self.is_previous_tournament_winner else '👤' if with_icon else ''
        return f'{icon} {self.mention_anon_name()}'.strip()


class Tournament(Base):
    __tablename__ = 'tournaments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)

    user_stats = relationship('UserTournamentStats', back_populates='tournament', cascade='all, delete-orphan')


class UserTournamentStats(Base):
    __tablename__ = 'user_tournament_stats'

    user_id = Column(BigInteger, ForeignKey('users.id'), primary_key=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'), primary_key=True)
    gems = Column(Integer, default=0)
    spins = Column(Integer, default=0)
    jackpots = Column(Integer, default=0)
    is_email_sent = Column(Boolean, default=False)

    user = relationship('User', back_populates='tournament_stats')
    tournament = relationship('Tournament', back_populates='user_stats')
