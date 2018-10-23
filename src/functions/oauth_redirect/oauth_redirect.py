import json
import logging
import os

from sqlalchemy import create_engine
from botocore.vendored import requests

from models import Session, SlackTeams

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
DOMAIN_NAME = os.getenv('DOMAIN_NAME')

DATABASE_ENDPOINT = os.getenv('DATABASE_ENDPOINT')
DATABASE_PORT = os.getenv('DATABASE_PORT')
DATABASE_USERNAME = os.getenv('DATABASE_USERNAME')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')

engine = create_engine(
    f'mysql+pymysql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@'
    f'{DATABASE_ENDPOINT}:{DATABASE_PORT}/jamfthegathering?charset=utf8'
)
Session.configure(bind=engine)


def save_new_team(token_data):
    session = Session()

    team = session.query(SlackTeams).filter(
        SlackTeams.team_id == token_data['team_id']).first()

    if team:
        logger.info(f"Updating Slack Team {team.team_id} with new access tokens...")
        team.access_token = token_data['access_token']
        team.bot_user_id = token_data['bot']['bot_user_id']
        team.bot_access_token = token_data['bot']['bot_access_token']
    else:
        logger.info(f"Creating new Slack Team: {token_data['team_id']}")
        team = SlackTeams(
            team_id=token_data['team_id'],
            team_name=token_data['team_name'],
            access_token=token_data['access_token'],
            bot_user_id=token_data['bot']['bot_user_id'],
            bot_access_token=token_data['bot']['bot_access_token']
        )
        session.add(team)

    try:
        session.commit()
    except:
        logger.exception('Unable to write new team to database')
        session.rollback()
        raise
    finally:
        session.close()


def response(message, status_code):
    """Returns a dictionary object for an API Gateway Lambda integration
    response.

    :param message: Message for JSON body of response
    :type message: str or dict

    :param int status_code: HTTP status code of response

    :rtype: dict
    """
    if isinstance(message, str):
        message = {'message': message}

    return {
        'isBase64Encoded': False,
        'statusCode': status_code,
        'body': json.dumps(message),
        'headers': {'Content-Type': 'application/json'}
    }


def get_access_tokens(code):
    r = requests.post(
        'https://slack.com/api/oauth.access',
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': code,
            'redirect_uri': f'https://{DOMAIN_NAME}/slack/oauth/redirect'
        }
    )
    return r.json()


def lambda_handler(event, context):
    code = event['queryStringParameters'].get('code')
    error = event['queryStringParameters'].get('error')

    if error:
        print(error)
        return response(error, 200)

    access_tokens = get_access_tokens(code)
    logger.info(f'Obtained access tokens: {access_tokens}')

    try:
        save_new_team(access_tokens)
    except:
        return response('failed', 500)

    return response('success', 200)
