import json
import logging
import os

from botocore.vendored import requests
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
Session.configure(bind=engine, expire_on_commit=False)


def get_or_create_user(session, data):
    logger.info(f"Looking up Slack team: {data['team_id']}")
    team = session.query(SlackTeams).with_entities(
        SlackTeams.id, SlackTeams.bot_access_token).filter(
        SlackTeams.team_id == data['team_id']).first()

    if not team:
        logger.error(
            f"The Slack user's team wasn't found! Team: {data['team_id']}")
        return None, None

    logger.info(f"Looking up Slack user: {data['event']['user']}")
    user = session.query(SlackUsers).filter(
        SlackUsers.user_id == data['event']['user']).first()

    if not user:
        logger.info(f"Creating new Slack user: {data['event']['user']}")

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
            return None, None

    return user, team


def send_chat_message(channel, text, token):
    r = requests.post(
        'https://slack.com/api/chat.postMessage',
        json={
            'channel': channel,
            'text': text,
            'link_names': True
        },
        headers={'Authorization': f'Bearer {token}'},
        timeout=5
    )
    logger.info(f"Slack API response: {r.status_code} {r.json()}")


def parse_card_list(string):
    try:
        int_list = [int(i) for i in string.strip().split()]
    except (TypeError, ValueError):
        return list()

    return int_list


def parse_trade(string):
    split = string.strip().partition('for')
    try:
        val1 = int(split[0].strip())
        val2 = int(split[2].strip())
    except (TypeError, ValueError):
        return None, None

    return val1, val2


def update_cards(user, type_, card_list, set_to=True):
    completed = list()
    for i in card_list:
        if 0 < i < 19:
            attr_name = f'{type_}_{i}'
            setattr(user, attr_name, set_to)
            completed.append(i)

    return completed


def process_command(session, message, user):
    have_completed = None
    need_completed = None
    commit = True
    message_text = ''

    if message.startswith('i have'):
        _, values = message.split('i have')
        card_list = parse_card_list(values)
        have_completed = update_cards(user, 'have', card_list)

    elif message.startswith('i need'):
        _, values = message.split('i need')
        card_list = parse_card_list(values)
        need_completed = update_cards(user, 'need', card_list)

    elif message.startswith('i traded'):
        _, values = message.split('i traded')
        trade = parse_trade(values)
        have_completed = update_cards(user, 'have', [trade[0]], False)
        need_completed = update_cards(user, 'need', [trade[1]], False)

    elif message.startswith('show trades'):
        commit = False

    else:
        return None

    if commit:
        try:
            session.commit()
        except:
            logger.exception(f"Unable to update Slack user '{user.user_id}'")
            session.rollback()
            return 'Whoops, something went wrong!'

    if have_completed:
        message_text += 'I have flagged the following cards as available for ' \
                        f'trade: {", ".join([str(i) for i in have_completed])}\n'
    if need_completed:
        message_text += 'I have flagged the following cards as needed from ' \
                        f'trade: {", ".join([str(i) for i in need_completed])}\n'

    if not message_text:
        message_text = "I'm sorry, I'm not sure what you wanted me to do?"

    return message_text


def lambda_handler(event, context):
    if event.get('Records'):
        logging.info('Processing SNS records...')
        for record in event['Records']:
            session = Session()
            session

            data = json.loads(record['Sns']['Message'])
            logger.info(data)

            user, team = get_or_create_user(session, data)

            if not (user and team):
                session.close()
                continue

            dm_user = False

            if data['event']['type'] == 'app_mention':
                dm_user = True
                source_text = \
                    data['event']['text'].lower().split(maxsplit=1)[-1]

            elif data['event']['type'] == 'message':
                source_text = data['event']['text'].lower()

            else:
                logger.warning(
                    f"Event type '{data['event']['type']}' is not supported...")
                continue

            message_text = process_command(session, source_text, user)
            session.close()

            if not message_text:
                logger.info('Unknown command or request')
                continue

            if dm_user:
                message_text = f'<@{user.user_id}> ' + message_text

            send_chat_message(
                data['event']['channel'],
                message_text,
                team.bot_access_token
            )

    else:
        logging.warning('No SNS records found in the event')

    return {}
