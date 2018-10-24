from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()
Session = sessionmaker()


class SlackTeams(Base):
    __tablename__ = 'slack_teams'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String(16), nullable=False, unique=True)
    team_name = Column(String(128), nullable=False)
    access_token = Column(String(128), nullable=False)
    bot_user_id = Column(String(12), nullable=False)
    bot_access_token = Column(String(64), nullable=False)

    users = relationship("SlackUsers", back_populates="slack_team")

    def serialize(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'team_name': self.team_name,
            'bot_user_id': self.bot_user_id
        }


class SlackUsers(Base):
    __tablename__ = 'slack_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(12), nullable=False)

    have_1 = Column(Boolean, default=False)
    have_2 = Column(Boolean, default=False)
    have_3 = Column(Boolean, default=False)
    have_4 = Column(Boolean, default=False)
    have_5 = Column(Boolean, default=False)
    have_6 = Column(Boolean, default=False)
    have_7 = Column(Boolean, default=False)
    have_8 = Column(Boolean, default=False)
    have_9 = Column(Boolean, default=False)
    have_10 = Column(Boolean, default=False)
    have_11 = Column(Boolean, default=False)
    have_12 = Column(Boolean, default=False)
    have_13 = Column(Boolean, default=False)
    have_14 = Column(Boolean, default=False)
    have_15 = Column(Boolean, default=False)
    have_16 = Column(Boolean, default=False)
    have_17 = Column(Boolean, default=False)
    have_18 = Column(Boolean, default=False)

    need_1 = Column(Boolean, default=False)
    need_2 = Column(Boolean, default=False)
    need_3 = Column(Boolean, default=False)
    need_4 = Column(Boolean, default=False)
    need_5 = Column(Boolean, default=False)
    need_6 = Column(Boolean, default=False)
    need_7 = Column(Boolean, default=False)
    need_8 = Column(Boolean, default=False)
    need_9 = Column(Boolean, default=False)
    need_10 = Column(Boolean, default=False)
    need_11 = Column(Boolean, default=False)
    need_12 = Column(Boolean, default=False)
    need_13 = Column(Boolean, default=False)
    need_14 = Column(Boolean, default=False)
    need_15 = Column(Boolean, default=False)
    need_16 = Column(Boolean, default=False)
    need_17 = Column(Boolean, default=False)
    need_18 = Column(Boolean, default=False)

    slack_team_id = Column(Integer, ForeignKey('slack_teams.id'))
    slack_team = relationship('SlackTeams', back_populates='users')

    def serialize(self):
        def attr_gttr(type_):
            card_dict = dict()
            for i in range(1, 19):
                attr_name = f'{type_}_{i}'
                card_dict[attr_name] = getattr(self, attr_name)

            return card_dict

        return {
            'id': self.id,
            'user_id': self.user_id,
            'slack_team_id': self.slack_team_id,
            'has': attr_gttr('have'),
            'needs': attr_gttr('need')
        }
