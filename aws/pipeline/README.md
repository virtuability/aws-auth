# Auth Pipeline

## Background

Infrastructure as Code for a serverless Cognito authentication & authorisation pipeline and application stacks.

To keep the application stack as simple as possible there is no requirement for a VPC.

## Set-up

### Pipeline

You will need to set-up a Secrets Manager secret store with the name `<application>-pipeline` (auth-pipeline or authdev-pipeline) and the following payload (disable key rotation).

```json
{
  "GitHubUser": "<GitHub user>",
  "GitHubToken": "<GitHub user token with access to github repository",
  "DevelopmentAccount": "<Development AWS Account Id>",
  "TestAccount": "<Test AWS Account Id>",
  "ProductionAccount": "<Production AWS Account Id>"
}
```

### Environments

You will also need to set-up a Secrets Manager secret store for each application stack with the name `<application>-<environment>` in the designated AWS account for each environment.

```json
```

## Deployment

### auth main test & production Pipeline

Create the Code pipeline and accompanying CodeBuild projects by running the following.

With `DEPLOY_APP` choose between the single-stage/environment authdev-pipeline and the multi-stage/environment auth-pipeline.

```bash
GIT_DIR=$HOME/ldev/git/virtuability/aws-auth
## Shared Services
DEPLOY_APP=authdev-pipeline|auth-pipeline
DEPLOY_ENV=shared-services
DEPLOY_ACCOUNT=`aws sts get-caller-identity | jq -r '.Account'`
AWS_DEFAULT_REGION=eu-west-1

# Validate template
cfn-lint $GIT_DIR/aws/pipeline/auth-pipeline.yaml

aws cloudformation validate-template --template-body file://$GIT_DIR/aws/pipeline/auth-pipeline.yaml

aws cloudformation package --template-file $GIT_DIR/aws/pipeline/auth-pipeline.yaml \
  --s3-bucket staging-${DEPLOY_ACCOUNT}-eu-west-1 \
  --s3-prefix ${DEPLOY_APP}/$DEPLOY_ENV \
  --output-template-file $GIT_DIR/aws/pipeline/${DEPLOY_APP}.packaged
```

Create the stack:

```bash
aws cloudformation create-stack --stack-name ${DEPLOY_APP} \
  --template-body file://$GIT_DIR/aws/pipeline/${DEPLOY_APP}.packaged \
  --parameters file://$GIT_DIR/aws/pipeline/parameters/${DEPLOY_APP}-${DEPLOY_ENV}.json \
  --tags Key=application,Value=${DEPLOY_APP} Key=environment,Value=$DEPLOY_ENV \
  --capabilities CAPABILITY_NAMED_IAM
```

Update the stack:

```bash
aws cloudformation update-stack --stack-name ${DEPLOY_APP} \
  --template-body file://$GIT_DIR/aws/pipeline/${DEPLOY_APP}.packaged \
  --parameters file://$GIT_DIR/aws/pipeline/parameters/${DEPLOY_APP}-${DEPLOY_ENV}.json \
  --tags Key=application,Value=${DEPLOY_APP} Key=environment,Value=$DEPLOY_ENV \
  --capabilities CAPABILITY_NAMED_IAM
```

An alternative recommendation is to use change-sets over update-stack to be able to review stack changes  prior to making them:

```bash
aws cloudformation create-change-set --change-set-name ${DEPLOY_APP} \
  --stack-name ${DEPLOY_APP} \
  --template-body file://$GIT_DIR/aws/pipeline/${DEPLOY_APP}.packaged \
  --parameters file://$GIT_DIR/aws/pipeline/parameters/${DEPLOY_APP}-${DEPLOY_ENV}.json \
  --tags Key=application,Value=${DEPLOY_APP} Key=environment,Value=$DEPLOY_ENV \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation execute-change-set --change-set-name ${DEPLOY_APP} \
  --stack-name ${DEPLOY_APP}
```
