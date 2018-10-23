import json
import os

from botocore.vendored import requests

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
DOMAIN_NAME = os.getenv('DOMAIN_NAME')


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
    print(access_tokens)

    return response('success', 200)
