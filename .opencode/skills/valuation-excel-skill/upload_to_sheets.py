import os
import io
import argparse
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def upload_sheet(company_name, excel_file_path):
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret_2_552117566971-h6q5mhlra2fdd4jbu17u75oemrjks0eo.apps.googleusercontent.com.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('drive', 'v3', credentials=creds)

        sheet_name = f'{company_name} Valuation (Auto-filled)'
        file_metadata = {
            'name': sheet_name,
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        
        media = MediaFileUpload(excel_file_path,
                                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                resumable=True)
                                
        # Check if file already exists
        query = f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])

        if items:
            file_id = items[0]['id']
            print(f"Found existing sheet '{sheet_name}'. Updating...")
            # Update existing file
            service.files().update(fileId=file_id, media_body=media).execute()
            # Fetch the webViewLink for the updated file
            file = service.files().get(fileId=file_id, fields='id, webViewLink').execute()
        else:
            print(f"Creating new sheet '{sheet_name}'...")
            file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        print(f"Success! File ID: {file.get('id')}")
        print(f"You can view your filled valuation sheet here: {file.get('webViewLink')}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Upload to Google Sheets")
    parser.add_argument("--company", type=str, required=True)
    parser.add_argument("--file", type=str, required=True)
    args = parser.parse_args()
    
    upload_sheet(args.company, args.file)
