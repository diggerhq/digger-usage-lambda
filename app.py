import os
import uuid
import json
import boto3
from datetime import datetime
from hashlib import sha256
import requests
import segment.analytics as analytics


USAGE_TABLE = os.environ["USAGE_TABLE"]
TOKEN = os.environ["TOKEN"]
SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK"]
SEGMENT_KEY = os.environ["SEGMENT_KEY"]
client = boto3.client("dynamodb")

analytics.write_key = SEGMENT_KEY

ignore_events_from = ["diggerhq", "Spartakovic", "motatoes", "veziak", "ZIJ", "UtpalJayNadiger", "carcunha", "terakoya76"]
repos_hashes_to_ignore_events_from = [sha256(org.encode("utf-8")).hexdigest() for org in ignore_events_from]

def app(event, context):
    print(event)
    payload = json.loads(event["body"])
    token = payload.get("token")
    if token != TOKEN:
        return {"statusCode": 500, "body": "token not valid"}

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    userid = payload.get("userid")

    if userid in repos_hashes_to_ignore_events_from or userid in ignore_events_from:
        return {"statusCode": 200, "body": "ok"}

    analytics.identify(userid)

    action = payload.get("action")
    event_name = payload.get("event_name")

    analytics.track(userid, action, {
        'event_name': event_name
    })

    client.put_item(
        TableName=USAGE_TABLE,
        Item={
            'pk': { 'S': str(uuid.uuid4())},
            'userid': {'S': userid},
            'action': {'S': action},
            'event_name': {'S': event_name},
            'timestamp': {'S': timestamp}
        },
    )

    if SLACK_WEBHOOK:
        requests.request("POST", SLACK_WEBHOOK, headers={"Content-type": "application/json"}, data=json.dumps({"text": f"New usage record. User id: {userid}. Action: {action}. Event name: {event_name}"}))

    return {"statusCode": 200, "body": "success"}

