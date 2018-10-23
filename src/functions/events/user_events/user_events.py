import json
import logging
import os

from sqlalchemy import create_engine

from models import Session, SlackTeams, SlackUsers

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DATABASE_ENDPOINT = os.getenv('DATABASE_ENDPOINT')
DATABASE_PORT = os.getenv('DATABASE_PORT')
DATABASE_USERNAME = os.getenv('DATABASE_USERNAME')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')

engine = create_engine(
    f'mysql+pymysql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@'
    f'{DATABASE_ENDPOINT}:{DATABASE_PORT}/jamfthegathering?charset=utf8'
)
Session.configure(bind=engine)


def get_or_create_user(data):
    session = Session()

    logger.info(f"Looking up Slack user: {data['event']['user']}")
    user = session.query(SlackUsers).filter(
        SlackUsers.user_id == data['event']['user']).first()

    if not user:
        logger.info(f"Creating new Slack user: {data['event']['user']}")

        team = session.query(SlackTeams).with_entities(
            SlackTeams.id).filter(
                SlackTeams.team_id == data['team_id']).first()

        if not team:
            logger.error(
                f"The Slack user's team wasn't found! Team: {data['team_id']}")
            return None

        user = SlackUsers(
            user_id=data['event']['user'],
            slack_team_id=team.id
        )

        try:
            session.add(user)
            session.commit()
        except:
            logger.exception('Unable to write new team to database')
            session.rollback()
            session.close()
            return None

    session.close()
    return user


def lambda_handler(event, context):
    if event.get('Records'):
        logging.info('Processing SNS records...')
        for record in event['Records']:
            data = json.loads(record['Sns']['Message'])
            logger.info(data)

            user = get_or_create_user(data)
            logger.info(user)

    else:
        logging.warning('No SNS records found in the event')

    return {}
