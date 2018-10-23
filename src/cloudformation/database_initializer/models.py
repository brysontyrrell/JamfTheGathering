from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SlackTeams(Base):
    __tablename__ = 'slack_teams'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String(16), nullable=False, unique=True)
    team_name = Column(String(128), nullable=False)
    access_token = Column(String(128), nullable=False)
    bot_user_id = Column(String(12), nullable=False)
    bot_access_token = Column(String(64), nullable=False)

    users = relationship("SlackUsers", back_populates="slack_team")


class SlackUsers(Base):
    __tablename__ = 'slack_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(12), nullable=False)

    slack_team_id = Column(Integer, ForeignKey('slack_teams.id'))
    slack_team = relationship('SlackTeams', back_populates='users')
