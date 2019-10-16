""" Lambda - handler: handler
"""

import os
import json
from copy import deepcopy
import logging.config
import yaml
from username_validator import UsernameValidator
from context_log import ContextLog

with open('resources/logging.yaml', 'r') as log_config_file:
  logging.config.dictConfig(yaml.safe_load(log_config_file))

USERNAME_VALIDATOR = UsernameValidator()

# Sourced from: https://github.com/ivolo/disposable-email-domains
# Use this to generate list: jq -r '.[]' index.json >resources/email-domain-blacklist.csv
EMAIL_DOMAIN_BLACKLIST_FILE = open("resources/email-domain-blacklist.csv", "r")
EMAIL_DOMAIN_BLACKLIST = EMAIL_DOMAIN_BLACKLIST_FILE.readlines()
EMAIL_DOMAIN_BLACKLIST = list(map(str.strip, EMAIL_DOMAIN_BLACKLIST))
EMAIL_DOMAIN_BLACKLIST_FILE.close()


def check_email_valid(email):
  """
  Check if email address is lower-case and valid as per the
  username_validator package
  """

  log = ContextLog.get_logger('check_email_valid')

  if email.islower():
    log.info('check_email_valid: email address is lower-case')
  else:
    log.warning('check_email_valid: email address is not all lower-case')
    raise Exception('Email must be lowercase')

  # Will raise and exception if invalid
  USERNAME_VALIDATOR.validate_all(email)


def check_email_domain_valid(email):
  """
  Check if email domain is in the exposable email domain list
  """

  log = ContextLog.get_logger('check_email_domain_valid')

  address = email.strip().split('@')

  if address[1] not in EMAIL_DOMAIN_BLACKLIST:
    log.info('check_email_domain_valid: email domain is not in disposable email domain list')
  else:
    log.warning('check_email_domain_valid: email domain is in disposable email domain list')
    raise Exception('Email domain is disposable')


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
    email = event['request']['userAttributes']['email']

    check_email_valid(email)

    # We don't validate the email domain if it's an Admin call.
    # The Admin call is made during user migration and we allow
    # them through.
    if event['triggerSource'] == 'PreSignUp_AdminCreateUser':
      log.info('handler: Admin call does not validate domain')
    else:
      check_email_domain_valid(email)

  except:
    log.exception('Invalid email')
    raise
  finally:
    ContextLog.put_end_time()
    log.info('Request: end')

  return event
