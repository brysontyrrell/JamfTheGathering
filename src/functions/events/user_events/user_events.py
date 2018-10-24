import json
import logging
import re
import os

from botocore.vendored import requests
from sqlalchemy import create_engine, or_

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


def read_user_cards(user, type_):
    attr_list = list()

    for i in range(1, 19):
        attr_name = f'{type_}_{i}'
        if getattr(user, attr_name):
            attr_list.append(attr_name)

    return attr_list


def command_show_trades(session, user):
    card_filter_list = list()

    user_have_list = read_user_cards(user, 'have')
    user_need_list = read_user_cards(user, 'need')

    filtered_need_list = [f"need_{i.split('_')[-1]}" for i in user_have_list]
    filtered_have_list = [f"have_{i.split('_')[-1]}" for i in user_need_list]

    for i in filtered_need_list:
        card_filter_list.append(
            getattr(user, i) == True)

    for i in filtered_have_list:
        card_filter_list.append(
            getattr(user, i) == True)

    results = session.query(SlackUsers)\
        .filter(
            SlackUsers.user_id != user.user_id,
            SlackUsers.slack_team_id == user.slack_team_id
        )\
        .filter(
            or_(*card_filter_list)
        ).all()

    message_text = 'Here are available trades for you:\n'
    if not results:
        message_text = 'Sorry, no trades available yet!'

    for ru in results:
        result_has_list = [i.split('_')[-1] for i in read_user_cards(ru, 'have') if i in filtered_have_list]
        result_need_list = [i.split('_')[-1] for i in read_user_cards(ru, 'need') if i in filtered_need_list]

        if result_has_list:
            has_string = f"has {', '.join(result_has_list)}"

        if result_need_list:
            need_string = f"needs {', '.join(result_need_list)}"

        message_text += f"<@{ru.user_id}> {' and '.join([l for l in (has_string, need_string) if l])}\n"

    return message_text


def process_command(input_text, session, user):
    commit = True
    message_text = ''

    try:
        if input_text.startswith('help'):
            message_text = \
                "Jamf the Gathering helps you find other JNUC attendees on " \
                "Slack who have cards to trade with you in your quest to " \
                "complete the full set of 18 cards!\n\nJust send me the " \
                "following commands to say which cards you have and which " \
                "cards you need:\n\n```\nI have 1 2 3\nI need 4 5 6```\nAs " \
                "you make trades, you can report them and update your " \
                "available caeds using:\n```I traded 1 2 for 4 5```\n" \
                "To find other users to trade with, type:```Show trades```"
        elif input_text.startswith('i have'):
            message_text = command_i_have(user, input_text)

        elif input_text.startswith('i need'):
            message_text = command_i_need(user, input_text)

        elif input_text.startswith('i traded'):
            message_text = command_i_traded(user, input_text)

        elif input_text.startswith('show trades'):
            message_text = command_show_trades(session, user)
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
        message_text = "I'm sorry, I'm not sure what you wanted me to do? " \
                       "Type 'Help' to learn how I work!"

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
