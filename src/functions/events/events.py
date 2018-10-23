import json


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
    print(body)

    event_type = body.get('type')
    challenge = body.get('challenge')

    print(f'Verification Type: {event_type}')
    print(f'Challenge: {challenge}')

    if event_type == 'url_verification' and challenge:
        print('Sending challenge response...')
        return response({'challenge': challenge}, 200)

    elif event_type == 'event_callback':
        print('Received an event!')
        return response('success', 200)

    else:
        print('Bad Request')
        return response('Bad Request', 400)
