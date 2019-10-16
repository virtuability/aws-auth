""" Lambda - handler: handler
"""

import os
import json
from copy import deepcopy
import boto3
from context_log import ContextLog

PUBLISH_USER_EVENTS = os.environ.get('PUBLISH_USER_EVENTS')
TOPIC_ARN = os.environ.get('USER_EVENT_TOPIC')
USER_POOL_ID = os.environ.get('USER_POOL_ID')

SNS_CLIENT = boto3.client('sns')

def publish_user_event(user_event):
  """
  Publish user events to SNS topic to decouple events from
  processing
  """
  if PUBLISH_USER_EVENTS.lower() == 'true':
    SNS_CLIENT.publish(
      TopicArn=TOPIC_ARN,
      Message=json.dumps({'default' : json.dumps(user_event)}),
      MessageStructure='json',
      Subject=user_event['type'] + '.' + user_event['result']
    )

def handler(event, context):
  """
  The Lambda handler entry point
  Called when a user is confirmed (link or email verification)
  """

  log = ContextLog.get_logger('handler', True)
  log.setLevel(os.environ.get('LOG_LEVEL', "DEBUG"))

  ContextLog.put_start_time()
  ContextLog.put_request_id(context.aws_request_id)
  ContextLog.put_request_user_id(event['request']['userAttributes']['email'])
  ContextLog.put_request_client_id(event['callerContext']['clientId'])
  ContextLog.put_trigger_source(event['triggerSource'])

  # Log event but remove any sensitive information
  user_event = deepcopy(event)

  log.info('Request: start - event %s', json.dumps(user_event))

  try:
    log.info('Sign-in event: %s', json.dumps(event))

    if event['triggerSource'] == 'PreAuthentication_Authentication':
      user_event['result'] = 'PRE_SIGNIN_SUCCESS'
    elif event['triggerSource'] == 'PostAuthentication_Authentication':
      user_event['result'] = 'POST_SIGNIN_SUCCESS'

  except:
    log.exception('Unexpected exception')
    user_event['result'] = 'ERROR'
    raise
  finally:
    publish_user_event(user_event)
    ContextLog.put_end_time()
    log.info('Request: end')

  return event
