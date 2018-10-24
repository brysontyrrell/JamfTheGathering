import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EVENTS_TOPIC = os.getenv('EVENTS_TOPIC')


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


def process_event(data):
    sns_client = boto3.client('sns')
    logger.info('Sending Slack event to be processed...')

    try:
        sns_client.publish(
            TopicArn=EVENTS_TOPIC,
            Message=json.dumps(data),
            MessageStructure='string'
        )
    except ClientError as error:
        logger.exception(f'Error sending SNS notification: {error}')


def lambda_handler(event, context):
    body = json.loads(event['body'])
    logger.info(body)

    event_type = body.get('type')
    logger.info(f'Event Type: {event_type}')

    if event_type == 'url_verification':
        logger.info('Sending challenge response...')

        challenge = body.get('challenge')
        logger.info(f'Challenge: {challenge}')

        return response({'challenge': challenge}, 200)

    elif event_type == 'event_callback':
        logger.info('Received an event!')
        if body['event'].get('subtype', '') == 'bot_message':
            logger.info('Ignoring bot message...')
            return response('OK', 200)

        if body['event']['type'] in ('app_mention', 'message'):
            process_event(body)
            return response('Accepted', 202)

    logger.warning('Bad Request')
    return response('Bad Request', 400)
