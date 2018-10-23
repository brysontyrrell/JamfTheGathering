import os

CLIENT_ID = os.getenv('CLIENT_ID')
DOMAIN_NAME = os.getenv('DOMAIN_NAME')


def lambda_handler(event, context):
    redirect_url = f'https://slack.com/oauth/authorize?client_id={CLIENT_ID}&' \
                   f'scope=bot,chat:write:bot&' \
                   f'redirect_uri=https://{DOMAIN_NAME}/slack/oauth/redirect'
    return {
        'isBase64Encoded': False,
        'statusCode': 302,
        'body': '',
        'headers': {'Location': redirect_url}
    }
