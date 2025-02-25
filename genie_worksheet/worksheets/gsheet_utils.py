from __future__ import print_function

import os
from typing import List

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CURR_DIR = os.path.dirname(os.path.realpath(__file__))

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def retrieve_gsheet(id, range):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = using_service_account()

    try:
        service = build("sheets", "v4", credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=id, range=range).execute()
        values: List = result.get("values", [])

        return values

    except HttpError as err:
        print(err)


def fill_all_empty(rows, desired_columns):
    for row in rows:
        for i in range(desired_columns - len(row)):
            row.append("")
    return rows


def using_service_account():
    # Path to your service account key file
    SERVICE_ACCOUNT_FILE = os.path.join(CURR_DIR, "service_account.json")

    # Scopes required by the Sheets API
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    # Create credentials using the service account key file
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )

    return credentials


def using_oauth2():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(os.path.join(CURR_DIR, "token.json")):
        creds = Credentials.from_authorized_user_file(
            os.path.join(CURR_DIR, "token.json"), SCOPES
        )
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(CURR_DIR, "credentials.json"), SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(os.path.join(CURR_DIR, "token.json"), "w") as token:
            token.write(creds.to_json())

    return creds
