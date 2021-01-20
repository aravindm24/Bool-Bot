from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
import io

# Documentation Links
# In-depth documentation:
# https://developers.google.com/resources/api-libraries/documentation/drive/v3/python/latest/drive_v3.files.html
# Tutorial Documentation:
# https://developers.google.com/drive/api/v3/about-files

# Temp Dir
temp_dir = "./bool_bot/files/"

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']

# Main Folder ID
main_folder_id = '1CeUaHMY5-Fm5XD36u3QWUZLaG6qAZUPq'

def authenticate():
    """
    Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'google-drive-credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds

def get_recent_files():
    """
    Returns the 10 most recent files

    return items : Array<Object(id, name)> - An array of objects/dicts with id and name attributes 
    """
    creds = authenticate()

    service = build('drive', 'v3', credentials=creds)

    # Call the Drive v3 API
    results = service.files().list(
        pageSize=10, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    return items

def get_file_id(filename):
    """
    Get file id from the name

    filename : String - The file name

    return found_files : Array<Object(id, name, webViewLink)> - The file id from google drive  
    """

    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    page_token = None
    response = service.files().list(q="name = '{0}'".format(filename), 
                                    pageSize=1,
                                    spaces="drive", 
                                    fields='nextPageToken, files(id, name, webViewLink)',
                                    pageToken=page_token).execute()

    return response["files"]

def download_photo(fileId, fileName):
    """
    Download the photo to local directory.

    fileId : String - The file id 
    fileName : String - The file name
    """
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    request = service.files().get_media(fileId=fileId)

    # print(request)

    # Downloads the photo to local storage. 
    fh = io.FileIO(temp_dir + fileName, mode='wb')
    downloader = MediaIoBaseDownload(fd=fh, request=request)


    done = False
    while done is False:
        status,done = downloader.next_chunk()
        # print("Download %d%%." % int(status.progress() * 100))
    
    fh.close()

    return fileName

def get_folder_ids(root_folder_id):
    """
    Returns all the sub folder IDs starting at root_folder(includes the root_folder ID). Goes one level deep.

    Ex: If the root folder has folder1, folder2 and folder3 in it, this will return a list of length 4 with the IDs associated
    with those 3 folders, and the ID of the root folder. However if the 3 folders have subfolders in them as well, this function will not return those subfolder IDs. 

    Note: If more than one level deep is needed, a recursive version can be implemented. However this might get very slow if the folder tree structure gets very
    complex. Refer to this if needed: https://stackoverflow.com/questions/41741520/how-do-i-search-sub-folders-and-sub-sub-folders-in-google-drive
    """
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    page_token = None
    response = service.files().list(q="mimeType = 'application/vnd.google-apps.folder' and '{}' in parents and trashed = false".format(root_folder_id), 
                                    pageSize=10,
                                    spaces="drive", 
                                    fields='nextPageToken, files(id, name, webViewLink)',
                                    pageToken=page_token,
                                    
                                    ).execute()
    
    found_ids = [response["files"][i]["id"] for i in range(0, len(response["files"]))] # extract all the IDs
    found_ids.append(root_folder_id) # if the Photos folder(as named on Google Drive) just contains folders, this is not needed

    return found_ids


def get_files_search(query):
    """
    Get the files that contains the query

    query : String - The query

    return found_files : Array<Object()> - The number of found files
    """

    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    folder_ids = get_folder_ids(main_folder_id)
    found_files = []

    for id in folder_ids:
        page_token = None
        response = service.files().list(q="name contains '{}' and '{}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'".format(query, id), 
                                        pageSize=10,
                                        spaces="drive", 
                                        fields='nextPageToken, files(id, name, webViewLink)',
                                        pageToken=page_token,
                                        
                                        ).execute()
        found_files.extend(response["files"]) # simply add to the current list of files found in other folders
        
    return found_files