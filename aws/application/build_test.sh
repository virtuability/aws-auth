
function headline {
  printf "\n\nInvoking $1 with $2 ...\n"
  printf "================================================================================\n\n"
}

sam build

headline "CognitoUserPreSignUpFunction" "CognitoUserPreSignUp_Disposable"
sam local invoke --env-vars local_env.json --event tests/CognitoUserPreSignUp_Disposable.json       rCognitoUserPreSignUpFunction

headline "CognitoUserPreSignUpFunction" "CognitoUserPreSignUp_Normal"
sam local invoke --env-vars local_env.json --event tests/CognitoUserPreSignUp_Normal.json           rCognitoUserPreSignUpFunction

headline "CognitoUserSignInFunction" "CognitoUserSignIn_PreAuthentication"
sam local invoke --env-vars local_env.json --event tests/CognitoUserSignIn_PreAuthentication.json   rCognitoUserSignInFunction

headline "CognitoUserSignInFunction" "CognitoUserSignIn_PostAuthentication"
sam local invoke --env-vars local_env.json --event tests/CognitoUserSignIn_PostAuthentication.json  rCognitoUserSignInFunction

headline "CognitoCreateUserPostConfirmationFunction" "CognitoCreateUserPostConfirmation"
sam local invoke --env-vars local_env.json --event tests/CognitoCreateUserPostConfirmation.json     rCognitoCreateUserPostConfirmationFunction
