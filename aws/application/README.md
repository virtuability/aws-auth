# Background

This directory contains the AWS infrastructure as code and source code for
the Cognito user migration and custom authentication integration lambda's.

# Testing

A series of local integration tests have been developed to test the 5 lambda
functions encompassing user migration and custom authentication (using
magic-link).

## Set-up

A local_env.json configuration file is required to run the tests. Here's an
example with obfuscated secrets. Create the file in this directory.

Note that the IP address `172.18.0.1` is a [Docker-specific gateway IP address](https://docs.docker.com/network/network-tutorial-standalone/) in which the lambda runs. This will differ depending on the host operating system (Linux, Windows or Mac).

Note that any values noted in `<>` will need to be substituted. Typically they are secrets that can be obtained from Secrets Manager (for development: authdev-development).

```
{
  "rCognitoBackupFunction" : {
    "LOG_LEVEL" : "DEBUG",
    "USER_POOL_ID" : "eu-west-1_icQTXivOS",
    "S3_BACKUP_BUCKET" : "authdev-development-cognito-backup"
  },
  "rCognitoUserPreSignUpFunction" : {
    "LOG_LEVEL" : "DEBUG"
  },
  "rCognitoUserSignInFunction" : {
    "LOG_LEVEL" : "DEBUG",
    "PUBLISH_USER_EVENTS" : "false",
    "USER_EVENT_TOPIC" : "arn:aws:sns:eu-west-1:123456789012:authdev-development-cognito-user-event",
    "USER_POOL_ID" : "eu-west-1_icQTXivOS"
  },
  "rCognitoCreateUserPostConfirmationFunction" : {
    "LOG_LEVEL" : "DEBUG",
    "PUBLISH_USER_EVENTS" : "false",
    "USER_EVENT_TOPIC" : "arn:aws:sns:eu-west-1:123456789012:authdev-development-cognito-user-event",
    "USER_POOL_ID" : "eu-west-1_icQTXivOS"
  },
  "ApiFunction" : {
    "LOG_LEVEL" : "DEBUG"
  }
}
```

## Running

To run the tests simply execute:

```
./build_test.sh
```
