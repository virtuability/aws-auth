# AWS Cognito-based Serverless Authentication Stack

## Background

This repository contains a full demonstration of a Cognito-based Serverless authentication & authorisation stack.

The stack contains the following components:

- Codepipeline and CodeBuild
- Cognito for authentication & authorisation
- API Gateway
- Lambda underpinning the API Gateway

## Pipeline

Builds and deployments are done via AWS Codepipeline. The pipeline stack exists - and is documented - in [aws/pipeline/README.md](aws/pipeline/README.md).

The example provides parameters for two different pipelines:

- authdev-pipeline single-stage pipeline containing a development environment
- auth-pipeline multi-stage pipeline containing test & production environments (also referred to as a route-to-live pipeline)

The parameter files used to instantiate each pipeline (auth-pipeline or authdev-pipeline) are located in `aws/pipeline/parameters`.

## Architecture

Cognito provides an authentication and authorization service. The service can authenticate users and app clients.

The user (id) and client (access) tokens that Cognito generates on successful authentication can be used to authorise clients and users to make lambda-api API backend calls.

Please refer to the [Limits in Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html) documentation for Cognito limits including token duration, user request throttling etc.

## Infrastructure as Code

All of the Cognito stack is built as Cloudformation infrastructure as code. The main template is [aws/application/template.yaml](aws/application/template.yaml).

The parameter files used to instantiate each of the three possible environments are located in `aws/application/parameters`.

## Integration

Cognito offers considerable integration and customisation through Lambdas. This includes for user migration, validation and messaging purposes. None of these integration features are included in this demonstration stack to keep the stack as simple as possible.

For more information, workflows and important points on Cognito Lambda integration refer to the Cognito [Customizing User Pool Workflows with Lambda Triggers](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools-working-with-aws-lambda-triggers.html) documentation.

At a high level the included integration encompasses the following areas:

- Validation:
  - CognitoUserPreSignUp: Validate email address and ensure it's not in the [disposable email domain blacklist](https://github.com/ivolo/disposable-email-domains)
- Logging: Emit logs to Cloudwatch Logs so that we can determine amount of failed and passed login requests
  - CognitoUserSignIn: Acts as Pre and Post sign-in trigger and emits user event logs to Cloudwatch Logs
  - CognitoCreateUserPostConfirmation: Logs user post confirmation

The Lambda's log entries that are used for CloudWatch metrics, which in turn are visualised on a CloudWatch Dashboard.

## Cognito Tokens

Note that all Cognito tokens are 1 hour in duration. This is a Cognito constraint and cannot currently be changed.

On successful authentication users are issued with 2 tokens:

- Access token, which is used to interact with the Cognito API to e.g. get and change user details
- ID token, which is used to present to an application API

It is possible to obtain user tokens using the AWS CLI as follows:

```bash
USER_ACCESS_TOKEN=`aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters 'USERNAME=tester1@gmail.com,PASSWORD=<password>' \
  --client-id <app client id in given user pool> | jq -r '.AuthenticationResult.AccessToken'`
```

## Cognito Clients

Cognito app clients are needed in all circumstances to obtain both client and user credentials. App clients consist of a client id, some URL configuration and optionally a client secret.

*Note that client secrets are only used for services integration and not used for apps as this is inherently insecure (storing secrets in publicly available apps.*

For services integration clients it is possible to obtain Cognito client tokens using a curl call as follows:

```bash
COGNITO_AUTH_ENDPOINT=<https://auth.dev.website-test.info|https://auth1.tst.website-test.info|https://auth.website-test.info>
COGNITO_INT_CLIENT_ID=<cognito client id>
COGNITO_INT_CLIENT_SECRET=<cognito client secret>

INT_CLIENT_ACCESS_TOKEN=`curl -X POST --user $COGNITO_INT_CLIENT_ID:$COGNITO_INT_CLIENT_SECRET \
 "$COGNITO_AUTH_ENDPOINT/oauth2/token?grant_type=client_credentials" \
 -H 'Content-Type: application/x-www-form-urlencoded' \
  | jq -r '.access_token'`
```

## Set-up

### Prerequisites

- Each AWS account must have been prepared with the [LZCrossAccount Cloudformation template](https://github.com/virtuability/aws-lz/blob/master/README.md)
- The Codepipeline requires a [properly configured GitHub Personal Access Token](https://docs.aws.amazon.com/codepipeline/latest/userguide/GitHub-create-personal-token-CLI.html)
- Create Route 53 hosted zones & domains for development, test and production stacks. In our example case we use: development: (auth.)dev.website-test.info, test: (auth.)tst.website-test.info and finally production: (auth.)website-test.info for Cognito
- Create - and validate - certificates for the domains above (in us-east-1 for Cloudfront - both in case of API Gateway and Cognito custom hosted domain name). One certificate to encompass both the parent domain and wildcarded sub-domains is possible, e.g. a certificate for development that has these two names in it is and option per environment: dev.website-test.info & *.dev.website-test.info

### Git repository

Clone (or fork) the repository locally:

```bash
GIT_DIR=$HOME/dev/git/virtuability/aws-auth
mkdir -p $GIT_DIR
cd $GIT_DIR/..
git clone https://github.com/virtuability/aws-auth.git
```

### S3 staging bucket

For each AWS account create an S3 bucket to:

```bash
AWS_ACCOUNT_ID=`aws sts get-caller-identity | jq -r '.Account'`
AWS_DEFAULT_REGION=eu-west-1
aws s3 mb s3://cfn-deploy-${AWS_ACCOUNT_ID}-${AWS_DEFAULT_REGION}
```

## Develoment

For local (developer) unit/integration tests refer to [aws/application/README.md](aws/application/README.md)
for more information.

For app stack integration tests refer to [tests/README.md](tests/README.md) for more information.

### Test pre-requisite tasks

If a new app stack has been stood up it will need to be seeded with new data in order for the tests to succeed. Furthermore emails and users need to exist and be configured in the tests.

- Use the Cognito link (`auth-<environment>` Cloudformation stack) to identify AndroidAppClientSignInUrl or IosAppClientSignInUrl. Open either link and create the user tester1@gmail.com.
- Login to the tester1@gmail.com gmail account and confirm the user
- Use the Cognito link again to login as a known existing user from the old authentication service (with same user password as in the old service) to ensure that user migration works, i.e. successful login

### Deployment

Refer to [aws/pipeline/README.md](aws/pipeline/README.md) for more information.
