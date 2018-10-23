import json
import logging
import os

from sqlalchemy import create_engine

from models import Session, SlackTeams, SlackUsers

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


def query_table(table):
    session = Session()

    try:
        results = session.query(table).all()
    except:
        logger.exception(f'Unable to read {table} from database')
        session.rollback()
        raise
    finally:
        session.close()

    return [i.serialize() for i in results]


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


def lambda_handler(event, context):
    try:
        teams = query_table(SlackTeams)
        users = query_table(SlackUsers)
    except:
        return response('failed', 500)

    return response({'Teams': teams, 'Users': users}, 200)
