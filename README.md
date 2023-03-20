# YouTube_Unban_Form
POC for an unban form

1) Create Google OAuth credentials and save to "client_secrets.json"
2) Modify `server.py` line #16 with the channel id of who is processing the unban forms
3) run the server: `python server.py`
4) When Prompted (2x in development) Visit the provided URL to authorize the app;
4.1) Ensure you authorize using the account that the members are banned from
4.2) Provide the script the code provided to you after authroization

5) Provide access to the server's interface via HTTP(S); and direct users to submit requests

6) visit the server's URL and preform an initial login
7) visit the server's URL /review_request to process the unban requests


## NOTES:
This is still in very early stages of development; and may not actually have any additional development preformed.

## Limitations:
Due to youtube's API; there is no way to check if the user is actually banned or not.
