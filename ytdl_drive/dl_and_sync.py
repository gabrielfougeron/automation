import subprocess
import os
from youtube_dl import YoutubeDL
import difflib
import time

ytdl_replace_rules = {
    "|": "_",
}

google_replace_rules = {
    "'": " ",
}

def str_replace(input_str, replace_rules = {}):
    
    res = input_str
    for key, val in replace_rules.items():
        res = res.replace(key, val)
    
    return res
    

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]

files_folder = os.path.join(os.path.dirname(__file__), 'files')

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


ydl_opts = {
    'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
    }],
    'outtmpl':os.path.join(files_folder, '%(title)s.%(ext)s'),
    'extractaudio': True,
    'audioformat': 'mp3',
}

n_retries_max = 10

ydl = YoutubeDL(ydl_opts)
ydl.add_default_info_extractors()

with open("url_list.txt","r") as f:
    lines = f.readlines()

for line in lines:
    playlist = ydl.extract_info(line, download=False)
    
    for video in playlist['entries']:
        print()
        print(f'Video #{video['playlist_index']}:  {video['title']}')
        
        filename = str_replace(video['title']+'.mp3', ytdl_replace_rules)
        full_filename = os.path.join(files_folder, filename)
        
        if not os.path.exists(full_filename):
        
            print("Audio file not found, downloading")
            
            success = False
            n_retries = 0
            
            while (not success) and (n_retries < n_retries_max):
                
                print(f'Attempt {n_retries+1} of {n_retries_max}')
            
                try:
                    ydl.download([video["webpage_url"]])
                    success = True
                except Exception as exc:
                    
                    print("Exception occurred")
                    print(exc)
                    print()
                    
                    n_retries += 1
                    
                time.sleep(1.)
        
            if success:
                print("Downloaded video and extracted audio")
            else: 
                print("Download failed")

        # if not os.path.exists(filename):
        #     
        #     for test_filename in os.listdir(files_folder):
        #         test_filename = os.path.join(files_folder, test_filename)
        #         
        #         difflib.SequenceMatcher
 
        if os.path.exists(full_filename):
            
            gdrive_filename = str_replace(filename, google_replace_rules)
            
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
            
            print(f'File found in Google Drive : {file_exists}')
            
            if not file_exists:
            
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
                
                print("Uploaded audio to Google Drive")
            
        else:
            print(filename)
            print("Where is file ????")
        
