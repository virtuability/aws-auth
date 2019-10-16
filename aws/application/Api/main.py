""" Lambda - handler: handler
"""

import os
import json
import logging.config
import yaml
import boto3
from context_log import ContextLog
import awsgi
from flask import Flask, jsonify

with open('resources/logging.yaml', 'r') as log_config_file:
  logging.config.dictConfig(yaml.safe_load(log_config_file))

app = Flask(__name__)

@app.route('/guest')
def guest():
  """
  The guest entry point
  """
  log = ContextLog.get_logger('guest')

  log.info('Guest request')

  return jsonify(status=200, message='OK')

@app.route('/user')
def user():
  """
  The guest entry point
  """
  log = ContextLog.get_logger('user')

  log.info('User request')

  return jsonify(status=200, message='OK')

def handler(event, context):
  """
  The Lambda handler entry point
  """

  log = ContextLog.get_logger('handler', True)
  log.setLevel(os.environ.get('LOG_LEVEL', 'DEBUG'))

  ContextLog.put_start_time()
  ContextLog.put_request_id(context.aws_request_id)

  log.info('Request: start - event %s', json.dumps(event))

  try:
    log.info('Request: running')

    return awsgi.response(app, event, context)

  except:
    log.exception('Unexpected exception')
    raise
  finally:
    ContextLog.put_end_time()
    log.info('Request: end')
