import subprocess
import os

# from youtube_dl import YoutubeDL
from yt_dlp import YoutubeDL

import difflib
import numpy as np
import time

def find_file_in_dir(directory, filename, thresh = 0.9):
    
    all_files = []
    all_scores = []
    
    for f in os.listdir(directory):
        fullname = os.path.join(directory, f)
        if os.path.isfile(fullname):
            all_files.append(fullname)
            all_scores.append(difflib.SequenceMatcher(None, f, filename).ratio())
            
    all_scores = np.array(all_scores)
    if all_scores.shape[0] > 0:
        idx_sort = np.argsort(all_scores)
        max_score = all_scores[idx_sort[-1]]
        
        if max_score > thresh:
            return all_files[idx_sort[-1]]
        else:
            return None
        
    else:
        return None
    
filename_replace_rules = {
    "'": "",
    "：": " ",
    "？": " ",
    "｜": " ",
    "⧸": " ",
    "＂": " ",
    "?": " ",
    "|": " ",
    ":": " ",
    "*": "",
    "<": "",
    ">": "",
    "/": " ",
    "+": " ",
    "[": " ",
    "]": " ",
    ":": " ",
    '"': " ",
    "'": " ",
    "é": "e",
    "è": "e",
    "ê": "e",
    "à": "a",
    "  ": " ",   
}

filename_start_replace_rules = {
    " ": "",  
}

def str_replace(input_str, rules = filename_replace_rules, start_rules = filename_start_replace_rules):
    
    res = input_str
    for key, val in rules.items():
        res = res.replace(key, val)
    
    for key, val in start_rules.items():
        while res.startswith(key):
            res = res[len(key):]
    
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
if not os.path.exists(files_folder):
    os.makedirs(files_folder)

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
main_folder_id = folder_list[0]["id"]


ydl_opts = {
    'quiet': True,
    # 'format': 'mp3/bestaudio/best',
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

with open("url_list.txt","r") as f:
    lines = f.readlines()

for iplaylist, line in enumerate(lines):

    line = line.replace('\n','')

    playlist = ydl.extract_info(line, download=False)
    
    playlist_title = str_replace(playlist["title"])

    print()
    print("="*50)
    print(f'Playlist {iplaylist+1} of {len(lines)}: {playlist_title}')
    print("="*50)
    
    playlist_dir = os.path.join(files_folder, playlist_title)
    
    if not os.path.exists(playlist_dir):
        os.makedirs(playlist_dir)
    
    # Does playlist exist in Gdrive ?

    folder_list = (
        service.files()
        .list(
            q=f"name='{playlist_title}' and '{main_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'",
            fields="files(id, name)",
        )
        .execute()
        .get("files", [])
    )
    
    if len(folder_list) == 0:
                
        playlist_folder_id = (
            service.files()
            .create(
                body = {
                    'name': playlist_title,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [main_folder_id],
                },
                fields='id')
            .execute().get('id')
        )
        
    else:
        playlist_folder_id = folder_list[0].get('id')
        

    
    n_videos = len(playlist['entries'])
    
    for video in playlist['entries']:
        print()
        print(f'Video #{video['playlist_index']} of {n_videos}: {video['title']}')
        
        filename = video['title']+'.mp3'
        
        print(f"Looking for audio file {filename}")
        
        full_filename = find_file_in_dir(playlist_dir, filename)

        if full_filename is None:
        
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
                
        else:
            print("Audio file found")

        # Again!
        for directory in [playlist_dir, files_folder]:
            full_filename = find_file_in_dir(directory, filename)
            if full_filename is not None:
                break
     
        if full_filename is not None:
            
            gdrive_filename = str_replace(filename)
            
            new_filename = os.path.join(playlist_dir, gdrive_filename)
            os.rename(full_filename, new_filename)

            for folder_id in [main_folder_id, playlist_folder_id]:
                
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
                
                if file_exists:
                    break
                
            print(f'File found in Google Drive : {file_exists}')
            
            if not file_exists:
            
                file_size = os.stat(new_filename).st_size
                mimetype = "audio/mpeg"
                chunksize = 262144
                media = MediaFileUpload(new_filename, mimetype=mimetype, resumable=True, chunksize=chunksize)

                request = (
                    service.files()
                    .create(
                        body = {
                            'parents' : [playlist_folder_id],
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
