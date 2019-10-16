""" Lambda - handler: handler
"""

import os
from smtplib import SMTP_SSL as SMTP
import json
from copy import deepcopy
import boto3
from context_log import ContextLog

PUBLISH_USER_EVENTS = os.environ.get('PUBLISH_USER_EVENTS')
TOPIC_ARN = os.environ.get('USER_EVENT_TOPIC')
USER_CHANGE_QUEUE = os.environ.get('USER_CHANGE_QUEUE')
USER_GROUP_NAME = os.environ.get('USER_GROUP_NAME')
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

  log = ContextLog.get_logger(True)
  log.setLevel(os.environ.get('LOG_LEVEL', "DEBUG"))

  ContextLog.put_start_time()
  ContextLog.put_request_id(context.aws_request_id)
  ContextLog.put_request_user_id(event['request']['userAttributes']['email'])
  ContextLog.put_request_client_id(event['callerContext']['clientId'])
  ContextLog.put_trigger_source(event['triggerSource'])

  # Log event - but remove any sensitive information
  user_event = deepcopy(event)

  log.info('Request: start - event %s', json.dumps(user_event))

  try:
    log.info('Processing: %s', event['triggerSource'])

    if event['triggerSource'] == 'PostConfirmation_ConfirmSignUp':

      user_event['result'] = 'CONFIRM_SIGNUP_SUCCESS'

    elif event['triggerSource'] == 'PostConfirmation_ConfirmForgotPassword':
      user_event['result'] = 'CONFIRM_FORGOT_PASSWORD_SUCCESS'

  except:
    log.exception('Unexpected exception')
    user_event['result'] = 'ERROR'
    raise
  finally:
    publish_user_event(user_event)
    ContextLog.put_end_time()
    log.info('Request: end')

  return event
