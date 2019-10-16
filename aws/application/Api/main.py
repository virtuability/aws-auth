""" Lambda - handler: handler
"""

import os
import json
from copy import deepcopy
import boto3
from context_log import ContextLog

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
    log.info('Doing stuff...')
  except:
    log.exception('Unexpected exception')
    raise
  finally:
    ContextLog.put_end_time()
    log.info('Request: end')

  return event
