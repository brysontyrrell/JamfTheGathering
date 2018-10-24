import json
import logging
import re
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

I_HAVE_RE = re.compile(r'^i\s+have\s+([\d\s]+)(?<!\s)\s*$')
I_NEED_RE = re.compile(r'^i\s+need\s+([\d\s]+)(?<!\s)\s*$')
I_TRADED_RE = re.compile(
    r'^i\s+traded\s+([\d\s]+)(?<!\s)\s+for\s+([\d\s]+)(?<!\s)\s*$')

engine = create_engine(
    f'mysql+pymysql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@'
    f'{DATABASE_ENDPOINT}:{DATABASE_PORT}/jamfthegathering?charset=utf8'
)
Session.configure(bind=engine, expire_on_commit=False)


class CommandException(Exception):
    pass


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


def parse_int_list(string):
    try:
        int_list = [int(i) for i in string.strip().split()]
    except (TypeError, ValueError):
        return list()

    return int_list


def update_cards(user, type_, card_list, set_to=True):
    completed = list()
    for i in card_list:
        if 0 < i < 19:
            attr_name = f'{type_}_{i}'
            setattr(user, attr_name, set_to)
            completed.append(i)

    return completed


def command_i_have(user, com_string):
    match = I_HAVE_RE.match(com_string)
    if not match:
        raise CommandException

    card_list = parse_int_list(match.group(1))
    completed = update_cards(user, 'have', card_list)

    return 'I have flagged the following cards available for trade: ' \
           f'{", ".join([str(i) for i in completed])}\n'


def command_i_need(user, com_string):
    match = I_NEED_RE.match(com_string)
    if not match:
        raise CommandException

    card_list = parse_int_list(match.group(1))
    completed = update_cards(user, 'need', card_list)

    return 'I have flagged the following cards as needing to trade for: ' \
           f'{", ".join([str(i) for i in completed])}\n'


def command_i_traded(user, com_string):
    match = I_TRADED_RE.match(com_string)
    if not match:
        raise CommandException

    trade_out_list = parse_int_list(match.group(1))
    trade_in_list = parse_int_list(match.group(2))

    traded_out = update_cards(user, 'have', trade_out_list, False)
    traded_in = update_cards(user, 'need', trade_in_list, False)

    return f'I have updated your cards!\n' \
           f'{", ".join([str(i) for i in traded_out])} ' \
           f'are no longer flagged for trading.\n' \
           f'{", ".join([str(i) for i in traded_in])} ' \
           f'are no longer flagged as needed'


def process_command(input_text, session, user):
    commit = True
    message_text = ''

    try:
        if input_text.startswith('i have'):
            message_text = command_i_have(user, input_text)

        elif input_text.startswith('i need'):
            message_text = command_i_need(user, input_text)

        elif input_text.startswith('i traded'):
            message_text = command_i_traded(user, input_text)

        elif input_text.startswith('show trades'):
            message_text = 'Here are available trades for you!\n...'
            commit = False
    except CommandException:
        message_text = 'Whoops, something went wrong!'
        commit = False

    if commit:
        try:
            session.commit()
        except:
            logger.exception(f"Unable to update Slack user '{user.user_id}'")
            session.rollback()
            return 'Whoops, something went wrong!'

    if not message_text:
        message_text = "I'm sorry, I'm not sure what you wanted me to do?"

    return message_text


def lambda_handler(event, context):
    if event.get('Records'):
        logging.info('Processing SNS records...')
        for record in event['Records']:
            session = Session()

            data = json.loads(record['Sns']['Message'])
            logger.info(data)

            user, team = get_or_create_user(session, data)

            if not (user and team):
                session.close()
                continue

            dm_user = False

            if data['event']['type'] == 'app_mention':
                dm_user = True
                input_text = \
                    data['event']['text'].lower().split(maxsplit=1)[-1]

            elif data['event']['type'] == 'message':
                input_text = data['event']['text'].lower()

            else:
                logger.warning(f"Event '{data['event']['type']}' is not supported!")
                continue

            message_text = process_command(input_text, session, user)
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
