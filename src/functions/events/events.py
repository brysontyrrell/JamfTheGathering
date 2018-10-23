import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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

        slack_event = body['event']
        if slack_event['type'] == 'app_mention':
            pass
        elif slack_event['type'] == 'message':
            pass

        return response('success', 200)

    else:
        logger.warning('Bad Request')
        return response('Bad Request', 400)
