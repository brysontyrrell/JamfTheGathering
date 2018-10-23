import json
import logging
import os

from botocore.vendored import requests
from sqlalchemy import create_engine

from models import Base

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


def create_database():
    logger.info('Creating database...')
    Base.metadata.create_all(engine)


def send_cf_response(event, context, success=True, reason='Unknown'):
    """This function sends a SUCCESS/FAILED response to the CloudFormation stack
    that invoked the Lambda function.
    """
    data = {
        'Status': 'SUCCESS' if success else 'FAILED',
        'PhysicalResourceId': context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId']
    }
    if not success:
        data['Reason'] = reason

    headers = {
        'Content-Type': ''
    }

    logger.info(data)
    logger.info(f"Sending CloudFormation response to {event['ResponseURL']}")
    resp = requests.put(
        event['ResponseURL'],
        data=json.dumps(data),
        headers=headers
    )
    logger.info(resp.status_code)


def lambda_handler(event, context):
    logger.info(f'Database Endpoint: {DATABASE_ENDPOINT}:{DATABASE_PORT}')
    logger.info(f'Database Username: {DATABASE_USERNAME}')

    try:
        create_database()
    except:
        logger.exception(
            'An error occurred while trying to create the database!')

    send_cf_response(event, context)
    return {}
