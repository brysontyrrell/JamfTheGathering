from sqlalchemy import Column, Integer, String, ForeignKey
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

    slack_team_id = Column(Integer, ForeignKey('slack_teams.id'))
    slack_team = relationship('SlackTeams', back_populates='users')

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'slack_team_id': self.slack_team_id
        }
