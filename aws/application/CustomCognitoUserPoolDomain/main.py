"""
Cloudformation Custom Cognito User Pool Domain Module
"""
import json
import logging.config
import re
import requests
import yaml
import boto3
from context_log import ContextLog

with open('resources/logging.yaml', 'r') as log_config_file:
    logging.config.dictConfig(yaml.safe_load(log_config_file))

COGNITO_IDP_CLIENT = boto3.client('cognito-idp')
SECRETSMANAGER_CLIENT = boto3.client('secretsmanager')

SUCCESS = "SUCCESS"
FAILED = "FAILED"
def send(event, context, responseStatus, response_data, physicalResourceId=None, noEcho=False):
    """
    From: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-lambda-function-code-cfnresponsemodule.html
    """
    log = ContextLog.get_logger('send')

    responseUrl = event['ResponseURL']

    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
    responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['NoEcho'] = noEcho
    responseBody['Data'] = response_data

    json_responseBody = json.dumps(responseBody)

    log.info('Response body: %s', json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = requests.put(responseUrl,
                                data=json_responseBody,
                                headers=headers)
        log.info('Status code: ' + response.reason)
    except Exception as ex:
        log.error('send(..) failed executing requests.put(..): %s', str(ex))

def handler(event, context):
    """
    Lambda main handler
    """
    log = ContextLog.get_logger('handler', True)

    ContextLog.put_start_time()
    ContextLog.put_request_id(context.aws_request_id)

    try:
        log.info('Request: start - event %s', json.dumps(event))

        user_pool_id = event['ResourceProperties']['UserPoolId']
        domain = event['ResourceProperties']['Domain']
        custom_domain_config = None

        if 'CustomDomainConfig' in event['ResourceProperties']:
            custom_domain_config = event['ResourceProperties']['CustomDomainConfig']
            log.info('Contains custom domain config found: %s', json.dumps(custom_domain_config))
            certificate_arn = custom_domain_config['CertificateArn']

            # Hack to support Secrets Manager as Cloudformation custom
            # resources do not presently support parameter resolution
            res = re.match('{{resolve:secretsmanager:(.+):SecretString:([a-zA-Z0-9-_:]+)}}', certificate_arn)
            if res:
                secret_id = res[1]
                attrib_str = res[2].split(':')
                secret_attribute = attrib_str[0] if len(attrib_str) > 0 else None
                args = {}
                if len(attrib_str) > 1:
                    args['VersionId'] = attrib_str[1]
                if len(attrib_str) > 2:
                    args['VersionStage'] = attrib_str[2]
                secret_response = SECRETSMANAGER_CLIENT.get_secret_value(SecretId=secret_id, **args)

                secret_obj = json.loads(secret_response['SecretString'])
                attribute_value = secret_obj[secret_attribute]

                log.info('Replacing certificate arn with SecretString: ...%s', attribute_value[-5:])

                custom_domain_config['CertificateArn'] = attribute_value

        response = None
        response_data = dict()

        if event['RequestType'] == 'Create':
            response = COGNITO_IDP_CLIENT.create_user_pool_domain(
                Domain=domain,
                UserPoolId=user_pool_id,
                CustomDomainConfig=custom_domain_config
            )
            response_data['Data'] = 'Created'

        elif event['RequestType'] == 'Update':

            # If domain name needs to be updated then we need to
            # delete the old domain and then create the new domain
            if 'OldResourceProperties' in event and event['OldResourceProperties']['Domain'] != event['ResourceProperties']['Domain']:
                delete_user_pool_domain(event['OldResourceProperties']['Domain'])

            response = COGNITO_IDP_CLIENT.create_user_pool_domain(
                Domain=domain,
                UserPoolId=user_pool_id,
                CustomDomainConfig=custom_domain_config
            )
            response_data['Data'] = 'Updated'

        elif event['RequestType'] == 'Delete':
            delete_user_pool_domain(event['ResourceProperties']['Domain'])
            response_data['Data'] = 'Deleted'

        else:
            send(event, context, FAILED, {'Data': 'Unexpected: {}'.format(event['RequestType'])})
            return

        if response and 'CloudFrontDomain' in response:
            log.info('create_user_pool_domain response includes CloudFrontDomain: %s', response['CloudFrontDomain'])
            response_data['CloudFrontDomain'] = response['CloudFrontDomain']

        send(event, context, SUCCESS, response_data)

        log.info('CognitoUserPoolDomain Success for request type %s', event['RequestType'])

    except Exception as ex:
        log.exception('Unexpected exception')
        send(event, context, FAILED, {'Data' : str(ex)})
        raise
    finally:
        ContextLog.put_end_time()
        log.info('Request: end')

def delete_user_pool_domain(domain):
    """
    Function to delete user pool domain
    """
    log = ContextLog.get_logger('delete_user_pool_domain')

    response = COGNITO_IDP_CLIENT.describe_user_pool_domain(
        Domain=domain
    )

    if 'UserPoolId' in response['DomainDescription']:
        log.info('domain exists - deleting: %s', domain)
        COGNITO_IDP_CLIENT.delete_user_pool_domain(
            Domain=domain,
            UserPoolId=response['DomainDescription']['UserPoolId']
        )
