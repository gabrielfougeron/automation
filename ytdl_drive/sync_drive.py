import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]

files_folder = "files/"

creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
        token.write(creds.to_json())
        
        
try:
    service = build("drive", "v3", credentials=creds)
    
    # Get folder ID
    
    results = (
        service.files()
        .list(q="name='YT_playlist' and mimeType = 'application/vnd.google-apps.folder'", fields="files(id, name)")
        .execute()
    )
    folder_list = results.get("files", [])
    assert len(folder_list) == 1
    folder_id = folder_list[0]["id"]

    for filename in os.listdir(files_folder):
        print()
        print(f'{filename = }')
        
        gdrive_filename = filename.replace("'", " ")

        results = (
            service.files()
            .list(
                q=f"name='{gdrive_filename}' and '{folder_id}' in parents",
                pageSize=5,
                fields="nextPageToken, files(id, name)",
            )
            .execute()
        )

        file_exists = (len(results.get("files", [])) > 0)
        
        print(f'{file_exists = }')
        
        if not file_exists:
            
            full_filename = os.path.join(files_folder, filename)
            file_size = os.stat(full_filename).st_size
            mimetype = "audio/mpeg"
            chunksize = 262144
            media = MediaFileUpload(full_filename, mimetype=mimetype, resumable=True, chunksize=chunksize)

            request = (
                service.files()
                .create(
                    body = {
                        'parents' : [folder_id],
                        'name': gdrive_filename,
                    },
                    media_body = media
                )
                .execute()
            )
            
except HttpError as error:
    print(f"An error occurred: {error}")
