# AWS Cognito-based Serverless Authentication Stack

## Background

This repository contains a full demonstration of a Serverless Cognito-based authentication & authorisation stack.

The stack contains the following components:

- AWS Codepipeline to perform source, build and deployment to development (single-stage pipeline) or test and production (multi-stage pipeline)
- AWS CodeBuild for build of application stack and code
- Cognito User Pool for user authentication
- Cognito custom domain with hosted UI where web browser users can sign-up, confirm account and sign-in
- Cognito Identity Pool to demonstrate both unauthenticated and authenticated access and exchange of Cognito token for temporary AWS credentials that can be used to interact with AWS services (in this case AWS PinPoint)
- Cognito Resource Server to demonstrate how to obtain OAuth2 client (service-to-service) credentials
- Cognito User Group to demonstrate how to add users to a group
- AWS Lambdas to demonstrate Cognito integration: User Pre-Signup trigger (validates email address and [email domain from a list of disposable email domains](https://github.com/ivolo/disposable-email-domains)), User Sign-in (used both Pre and Post) trigger, Post-Signup trigger
- API Gateway to demonstrate user and guest access
- AWS Lambda underpinning the API Gateway to demonstrate guest and user access via ID token
- AWS SNS topic where that user events are posted to (creation and sign-in)
- AWS CloudWatch Log Groups (with automatic encryption applied via custom resource)
- AWS CloudWatch Dashboard for runtime metrics surrounding the AWS Lambdas

Cognito - without the advanced option, which is relatively expensive - has no inherent CloudWatch metrics out-of-the-box. As a result it's hard to determine how many users sign-up, sign-in etc. A Dashboard has therefore been included, which includes the data from the Cognito Lambda triggers.

The application stack does not include a VPC. Aside from added complexity, adding Lambdas to a VPC considerably increase Lambda cold-start times, often past the maximum allowed 5 second runtime allowed by Cognito when calling a Lambda trigger (with 3 attemps).

*NOTE that this is a work-in-progress*. TODO list includes:

- Demonstrate use of client (service-to-service) credentials against API Gateway
- Demonstrate use of CodeBuild test stage/action to perform automated integration tests against Cognito and indeed the API Gateway

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

## Authentication

User authentication to Cognito can be performed via the [Secure Remote Password (SRP) protocol](https://www.ietf.org/rfc/rfc2945.txt). This protocol offers strong protection against password attacks and weak passwords.

However, implementing the SRP protocol can be complex if it's not natively supported by a client-side Cognito library or by the AWS CLI.

Therefore, for simplicity this stack allows the USER_PASSWORD_AUTH authentication flow. This flow enables authentication to be performed by sending both the username and password to Cognito for authentication in one request.

For production stacks, if USER_PASSWORD_AUTH is not necessary (e.g. where user migration to Cognito is either not needed or is complete) then it should be disabled for additional end-user security with SRP only.

Note that for Python there now exists a [warrant library](https://github.com/capless/warrant#cognito-srp-utility), which has an SRP utility.

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

## Tokens

Note that all Cognito tokens are currently 1 hour in duration. This is a Cognito constraint and cannot currently be changed.

Also note that the issued tokens are in [JSON Web Token](https://jwt.io/) format and can be decoded as such using said website.

Furthermore, note that tokens are signed by Cognito using a private key (RSA256) and can be verified with custom integration code using the public key. The public key can be retrieved from the Cognito User Pool endpoint, i.e. `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>/.well-known/jwks.json` with for instance `curl`.

During private key rotation multiple public keys may be available in `jwks.json`. Make sure to find the right key when verifying the token. The key id can be used to identify the correct key and is present in the first part of each issued JWT token (`kid`) alongside the algorithm (`alg`), which for Cognito is RSA256.

There are a wide variety of libraries listed on the [jwt.io website](https://jwt.io/#libraries), which can perform validation of the issued Cognito tokens.

### User tokens

On successful authentication users are issued with 3 different tokens:

- Access token, which is used to interact with the Cognito API to e.g. get and change user details
- ID token, which is used to present to an API for user access
- Refresh token, which is used to obtain another set of tokens later on without the need to sign-in again

It is possible to obtain the three tokens using the AWS CLI as follows (more advanced shell usage later):

```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters 'USERNAME=<username>,PASSWORD=<password>' \
  --client-id <app client id in given user pool>
```

## Cognito Clients

Cognito app clients are needed in all circumstances to obtain both client and user credentials. App clients consist of a client id, some URL configuration and optionally a client secret.

*Note that client secrets are only used for services integration and not used for apps as this is inherently insecure (storing secrets in publicly available apps.*

For services integration clients it is possible to obtain Cognito client tokens using a curl call as follows:

```bash
COGNITO_AUTH_ENDPOINT=<https://auth.dev.website-test.info|https://auth.tst.website-test.info|https://auth.website-test.info>
COGNITO_INT_CLIENT_ID=<cognito client id>
COGNITO_INT_CLIENT_SECRET=<cognito client secret>

INT_CLIENT_ACCESS_TOKEN=`curl -X POST --user $COGNITO_INT_CLIENT_ID:$COGNITO_INT_CLIENT_SECRET \
 "$COGNITO_AUTH_ENDPOINT/oauth2/token?grant_type=client_credentials" \
 -H 'Content-Type: application/x-www-form-urlencoded' \
  | jq -r '.access_token'`
```

## Set-up

### Prerequisites

- The AWS account must have been prepared with the [cross-account Cloudformation templates](https://github.com/virtuability/aws-lz/blob/master/README.md). Note the distinction between a Shared Services account and one or more Environment accounts (although they can all be one and the same account)
- The Codepipeline requires a [properly configured GitHub Personal Access Token](https://docs.aws.amazon.com/codepipeline/latest/userguide/GitHub-create-personal-token-CLI.html) to monitor the `master` branch of the repository
- Create Route 53 hosted zones and domain for development, test and production stacks. In our example case we use: development: (auth.)dev.website-test.info, test: (auth.)tst.website-test.info and finally production: (auth.)website-test.info for Cognito - we have a single domain (website-test.info) registered and it has NS records for the dev. and tst. sub-domains
- If a naked A record doesn't exist in each of these hosted zones then the Cognito UserPoolDomain will fail to create with the error: *Custom domain is not a valid subdomain: Was not able to resolve the root domain, please ensure an A record exists for the root domain.* Please add an (arbitrary A naked record to domain) - it's a strange requirement and I got no great response from AWS Support other than "proving ownership"
- Create - and validate - certificates for the domains above (in us-east-1 for Cloudfront - both in case of API Gateway and Cognito custom hosted domain name). One certificate to encompass both the parent domain and wildcarded sub-domains is possible, e.g. a certificate for development that has these two names in it is an option for each environment: dev.website-test.info & *.dev.website-test.info,  tst.website-test.info & *.tst.website-test.info and finally for production website-test.info & *.website-test.info

### Git repository

Fork the repository to your own github account.

Then clone the repository.

```bash
GIT_DIR=$HOME/dev/git/virtuability/aws-auth
mkdir -p $GIT_DIR
cd $GIT_DIR/..
git clone https://github.com/virtuability/aws-auth.git
```

### S3 staging bucket

For each AWS account create an S3 bucket:

```bash
AWS_ACCOUNT_ID=`aws sts get-caller-identity | jq -r '.Account'`
AWS_DEFAULT_REGION=eu-west-1
aws s3 mb s3://cfn-deploy-${AWS_ACCOUNT_ID}-${AWS_DEFAULT_REGION}
```

## Develoment

For local (developer) unit/integration tests refer to [aws/application/README.md](aws/application/README.md) for more information.

For app stack integration tests refer to [tests/README.md](tests/README.md) for more information.

### Test pre-requisite tasks

If a new app stack has been stood up it will need to be seeded with new data in order for the tests to succeed. Furthermore emails and users need to exist and be configured in the tests.

- Use the Cognito link (`auth-<environment>` Cloudformation stack) to identify AndroidAppClientSignInUrl or IosAppClientSignInUrl. Open either link and create the user tester1@gmail.com.
- Login to the tester1@gmail.com gmail account and confirm the user
- Use the Cognito link again to login as a known existing user from the old authentication service (with same user password as in the old service) to ensure that user migration works, i.e. successful login

### Deployment

Refer to [aws/pipeline/README.md](aws/pipeline/README.md) for more information.

## Cognito Usage

It is possible to use the AWS CLI to test many Cognito use cases. This section demonstrates how.

Prerequisites is to have a valid set of AWS credentials configured to be able to make the following calls.

First, some set-up of environment variables:

```bash
DEPLOY_APP=authdev
DEPLOY_ENV=development
AWS_DEFAULT_REGION=eu-west-1

# Get user pool id by name
COGNITO_USER_POOL=`aws cognito-idp list-user-pools \
  --max-results 10 \
  | jq -r ".UserPools[] | select (.Name == \"$DEPLOY_APP-$DEPLOY_ENV-user-pool\") | .Id"`

COGNITO_IDENTITY_POOL=`aws cognito-identity list-identity-pools \
  --max-results 10 \
  | jq -r ".IdentityPools[] | select (.IdentityPoolName == \"${DEPLOY_APP}${DEPLOY_ENV}\") | .IdentityPoolId"`
```

### Cognito User Pool UI - User creation and authentication

The provided solution adds a custom domain for hosting user registration and login pages, which can be used by your users for web-based sign-up and login. The URL can be put together with the following commands:

```bash
COGNITO_CUSTOM_DOMAIN=`aws cognito-idp describe-user-pool \
  --user-pool-id $COGNITO_USER_POOL \
  | jq -r ".UserPool.CustomDomain"`

COGNITO_ANDROID_CLIENT_ID=`aws cognito-idp list-user-pool-clients \
  --user-pool-id $COGNITO_USER_POOL \
  | jq -r ".UserPoolClients[] | select (.ClientName == \"$DEPLOY_APP-$DEPLOY_ENV-android-client\") | .ClientId"`

echo "Custom domain sign-up URL: https://$COGNITO_CUSTOM_DOMAIN/signup?response_type=code&client_id=$COGNITO_ANDROID_CLIENT_ID&redirect_uri=https://$COGNITO_CUSTOM_DOMAIN/auth/callback"

echo "Custom domain login URL: https://$COGNITO_CUSTOM_DOMAIN/login?response_type=code&client_id=$COGNITO_ANDROID_CLIENT_ID&redirect_uri=https://$COGNITO_CUSTOM_DOMAIN/auth/callback"
```

### AWS CLI User Pool User creation, authentication and deletion

This section shows how to use the AWS CLI to first create and verify a Cognito user; then authenticate as the user; and finally to delete the user.

Get android client id:

```bash
# Get android client by name
COGNITO_ANDROID_CLIENT_ID=`aws cognito-idp list-user-pool-clients \
  --user-pool-id $COGNITO_USER_POOL \
  | jq -r ".UserPoolClients[] | select (.ClientName == \"$DEPLOY_APP-$DEPLOY_ENV-android-client\") | .ClientId"`
```

Sign-up a user (adjust email address to one you control):

```bash
COGNITO_USERNAME=cognito.tester1@gmail.com
# Generate random password
COGNITO_USER_PWD=`< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c10`

# Sign-up user - this will send an email
aws cognito-idp sign-up \
  --client-id $COGNITO_ANDROID_CLIENT_ID \
  --username $COGNITO_USERNAME \
  --password $COGNITO_USER_PWD

# Confirm sign-up of user (as the user)
aws cognito-idp confirm-sign-up \
  --client-id $COGNITO_ANDROID_CLIENT_ID \
  --username $COGNITO_USERNAME \
  --confirmation-code 018599
```

*Alternatively*, you may confirm the user as a Cognito administrator. This verifies the user - but not the user's email address. This distinction is visible in issued id tokens with the following field `"email_verified": false`:

```bash
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id $COGNITO_USER_POOL \
  --username $COGNITO_USERNAME
```

As an admininistrator, add user to a Cognito group. When a user is a member of one or more groups this is reflected in both the access and ID token attribute `"cognito:groups": ["authdev-development-public-app-user"]`. The group in turn can be mapped to an IAM role that provides limited AWS permissions to allow users to interact with AWS Services in the AWS account.

```bash
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $COGNITO_USER_POOL \
  --username $COGNITO_USERNAME \
  --group-name $DEPLOY_APP-$DEPLOY_ENV-public-app-user
```

Now, sign-in as the user and get tokens:

```bash
# Return array with index 0 = AccessToken, 1 = IdToken and 2 = RefreshToken
USER_TOKENS=($(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters "USERNAME=$COGNITO_USERNAME,PASSWORD=$COGNITO_USER_PWD" \
  --client-id $COGNITO_ANDROID_CLIENT_ID \
  | jq -r ".AuthenticationResult | .AccessToken + \" \" + .IdToken + \" \" + .RefreshToken"))
```

If a user at this stage is confirmed (by an administrator) but the user's email isn't confirmed then the user can still login. The user can then confirm the email attribute themselves by requesting an email containing a code as follows:

```bash
aws cognito-idp get-user-attribute-verification-code \
  --access-token ${USER_TOKENS[0]} \
  --attribute-name email

aws cognito-idp verify-user-attribute \
  --access-token ${USER_TOKENS[0]} \
  --attribute-name email \
  --code 123456
```

Get the user's details from Cognito using the AccessToken:

```bash
aws cognito-idp get-user --access-token ${USER_TOKENS[0]}
```

*Alternatively*, you may as an administrator get the user details. Unlike when the user retrieves information about him or herself, the administrator call includes additional information like user status, when the user was created and whether the user account is enabled:

```bash
aws cognito-idp admin-get-user \
  --user-pool-id $COGNITO_USER_POOL \
  --username $COGNITO_USERNAME
```

Finally, delete the user (as the user). Don't do this if you want to work with the identity pool too (next section):

```bash
aws cognito-idp delete-user --access-token ${USER_TOKENS[0]}
```

### AWS CLI Identity Pool - unauthenticated/guest users

The Cognito identity pool enables integration with Cognito and other identity providers like Amazon and Google. It also acts as an OAuth token provider where tokens can be exchanged for temporary AWS account credentials that provide limited access to AWS services, which you specify.

Furthermore it enables unauthenticated users to obtain AWS account credentials that also provide limited access to AWS Services, which you specify.

To get an unauthenticated id you can call the identity provider:

```bash
COGNITO_UNAUTH_IDENTITY_ID=`aws cognito-identity get-id \
  --identity-pool-id $COGNITO_IDENTITY_POOL \
  | jq -r ".IdentityId"`
```

To get (exchange) limited AWS account credentials for the unauthenticated id use the following command. It conveniently outputs AWS account credentials as a triple of environment variables that can be defined in a new Shell.

```bash
aws cognito-identity get-credentials-for-identity \
  --identity-id $COGNITO_UNAUTH_IDENTITY_ID \
  | jq -r ".Credentials | \"export AWS_ACCESS_KEY_ID=\" + .AccessKeyId + \"\nexport AWS_SECRET_ACCESS_KEY=\" + .SecretKey + \"\nexport AWS_SESSION_TOKEN=\" + .SessionToken + \"\n\""
```

To use the temporary unauthorised account credentials we can generate an AWS Pinpoint Endpoint and Event on the Pinpoint app that is created as part of the application stack (permissions to do so are provided via the application stack rCognitoUnAuthorizedRole role). First let's get the Pinpoint app id:

```bash
aws pinpoint get-apps \
  | jq -r ".ApplicationsResponse.Item[] | select (.Name == \"$DEPLOY_APP-$DEPLOY_ENV-app\") | \"PINPOINT_APP_ID=\" + .Id"
```

To record the Endpoint and Event run the export the AWS account credentials from above as well as the Pinpoint app id following in the second shell - and finally the Pinpoint put-events call. The payload is just a structure of dummy values (that populates the AWS Pinpoint Dashboards):

```bash
# export AWS_ACCESS_KEY_ID=...
# export AWS_SECRET_ACCESS_KEY=...
# export AWS_SESSION_TOKEN=...
# PINPOINT_APP_ID=...

aws pinpoint put-events --application-id $PINPOINT_APP_ID \
  --events-request '{"BatchItem": { "p1": { "Endpoint": { "Demographic": { "AppVersion": "1.0"}},  "Events": { "e1": { "AppPackageName": "MyApp", "EventType": "xyz", "Timestamp": "2019-11-04T18:30:00Z"}}}}}'
```

### AWS CLI Identity Pool - authenticated users

The Cognito identity pool enables integration with Cognito and other identity providers like Amazon and Google. It also acts as an OAuth token provider where tokens can be exchanged for temporary AWS account credentials that provide limited access to AWS services, which you specify.

Furthermore it enables authenticated users to obtain AWS account credentials that also provide limited access to AWS Services, which you specify.

To get an authenticated id you can call the identity provider:

```bash
COGNITO_ID_PROVIDER=cognito-idp.$AWS_DEFAULT_REGION.amazonaws.com/$COGNITO_USER_POOL

COGNITO_AUTH_IDENTITY_ID=`aws cognito-identity get-id \
  --identity-pool-id $COGNITO_IDENTITY_POOL --logins "$COGNITO_ID_PROVIDER=${USER_TOKENS[1]}" \
  | jq -r ".IdentityId"`
```

To get (exchange) limited AWS account credentials for the unauthenticated id use the following command. It conveniently outputs AWS account credentials as a triple of environment variables that can be defined in a new Shell.

```bash
aws cognito-identity get-credentials-for-identity \
  --identity-id $COGNITO_AUTH_IDENTITY_ID --logins "$COGNITO_ID_PROVIDER=${USER_TOKENS[1]}" \
  | jq -r ".Credentials | \"export AWS_ACCESS_KEY_ID=\" + .AccessKeyId + \"\nexport AWS_SECRET_ACCESS_KEY=\" + .SecretKey + \"\nexport AWS_SESSION_TOKEN=\" + .SessionToken + \"\n\""
```

To use the temporary unauthorised account credentials we can generate an AWS Pinpoint Endpoint and Event on the Pinpoint app that is created as part of the application stack (permissions to do so are provided via the application stack rCognitoUnAuthorizedRole role). First let's get the Pinpoint app id:

```bash
aws pinpoint get-apps \
  | jq -r ".ApplicationsResponse.Item[] | select (.Name == \"$DEPLOY_APP-$DEPLOY_ENV-app\") | \"PINPOINT_APP_ID=\" + .Id"
```

To record the Endpoint and Event run the export the AWS account credentials from above as well as the Pinpoint app id following in the second shell - and finally the Pinpoint put-events call. The payload is just a structure of dummy values (that populates the AWS Pinpoint Dashboards):

```bash
# export AWS_ACCESS_KEY_ID=...
# export AWS_SECRET_ACCESS_KEY=...
# export AWS_SESSION_TOKEN=...
# PINPOINT_APP_ID=...

aws pinpoint put-events --application-id $PINPOINT_APP_ID \
  --events-request '{"BatchItem": { "p1": { "Endpoint": { "Demographic": { "AppVersion": "1.0"}},  "Events": { "e1": { "AppPackageName": "MyApp", "EventType": "xyz", "Timestamp": "2019-11-04T18:30:00Z"}}}}}'
```

### Authenticated API access

As part of the Cognito application stack an API Gateway has been included to demonstrate unauthenticated versus authenticated HTTPS endpoint access. A single ApiFunction Lambda is exposed through the API Gateway with two paths: /guest and /user.

First define the API Gateway endpoint environment variable, e.g.:

```bash
API_DOMAIN=https://api.dev.website-test.info
```

To access as guest (unauthenticated) just curl the endpoint:

```bash
curl $API_DOMAIN/guest
```

It should return:

```json
{"message":"OK","status":200}
```

To access as a user first attempt to curl the endpoint without a Cognito JWT token:

```bash
curl -v $API_DOMAIN/user
```

It should return (with a 401 response from the `-v` output):

```json
{"message":"Unauthorized"}
```

Now try user access with the ID token:

```bash
curl -v -H "Authorization: Bearer ${USER_TOKENS[1]}" $API_DOMAIN/user
```

It should return (with a 200 response from the `-v` output):

```json
{"message":"OK","status":200}
```

### Client authentication with OAuth2

This section shows how to get client credentials using client id and client secret. This flow is used to allowing API clients (a service; not a user) to access an API that is protected by Cognito.

Get machine client id and secret:

```bash
# Get machine client by name
COGNITO_MACHINE_CLIENT_ID=`aws cognito-idp list-user-pool-clients \
  --user-pool-id $COGNITO_USER_POOL \
  | jq -r ".UserPoolClients[] | select (.ClientName == \"$DEPLOY_APP-$DEPLOY_ENV-machine-client\") | .ClientId"`

COGNITO_MACHINE_CLIENT_SECRET=`aws cognito-idp describe-user-pool-client \
  --user-pool-id $COGNITO_USER_POOL --client-id $COGNITO_MACHINE_CLIENT_ID \
  | jq -r ".UserPoolClient | .ClientSecret"`
```

Authenticate as the client to get a token:

```bash
COGNITO_AUTH_ENDPOINT=https://`aws cognito-idp describe-user-pool --user-pool-id $COGNITO_USER_POOL | jq -r " .UserPool.CustomDomain"`

# Get the access token
MACHINE_ACCESS_TOKEN=`curl -s -X POST --user $COGNITO_MACHINE_CLIENT_ID:$COGNITO_MACHINE_CLIENT_SECRET \
 "$COGNITO_AUTH_ENDPOINT/oauth2/token?grant_type=client_credentials" \
 -H 'Content-Type: application/x-www-form-urlencoded' \
  | jq -r '.access_token'`
```
