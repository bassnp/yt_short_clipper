import time
import datetime
import pickle
import os
os.environ["IMAGEIO_FFMPEG_EXE"] = "C:\\Users\\bass\\Desktop\\py\\ffmpeg.exe"
import random
import math

from redvid import Downloader
from moviepy.editor import VideoFileClip

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as Ec

def log(str):
    print("[Scraper] " + str)
    time.sleep(0.5)
    
# Upload and schedule the videos
def create_service(client_secret_file, api_name, api_version, *scopes):
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]

    cred = None
    pickle_file = f"token_{API_SERVICE_NAME}_{API_VERSION}.pickle"

    if os.path.exists(pickle_file):
        with open(pickle_file, "rb") as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()

        with open(pickle_file, "wb") as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        return service
    except Exception as e:
        print("!!Unable to connect!!")
        print(e)
        return None
    
last_day = None
last_day = datetime.datetime.now().date()

while True:
    today = datetime.datetime.now().date()
    if today != last_day:
        last_day = today
        
        # Start selenium process
        log("Loading driver")
        options = Options()
        options.add_experimental_option("detach", True)
        driver = webdriver.Chrome(
            service = Service(ChromeDriverManager().install()),
            options = options
        )
        # https://www.reddit.com/r/Damnthatsinteresting/top/?t=day
        # https://www.reddit.com/r/PublicFreakout/top/?t=day

        driver.get("https://www.reddit.com/r/PublicFreakout/top/?t=day")
        log("Starting")

        # Find posts on page (old style)
        post_list = []
        try:
            scroll_body = WebDriverWait(driver, 10).until(
                Ec.presence_of_element_located((By.CLASS_NAME, "rpBJOHq2PR60pnwJlUyP0"))
            )
            log("Found body")
            
            for i in range(3):
                log("Entering: " + str(i))
                try: 
                    count = str(i + 2)
                    
                    title = driver.find_element(By.XPATH,
                        "/html/body/div[1]/div/div[2]/div[2]/div/div/div/div[2]/div[4]/div[1]/div[4]/div[" + count + "]/div/div/div[3]/div[2]/div[1]/a/div/h3").text
                    
                    holder = driver.find_element(By.XPATH,
                        "/html/body/div[1]/div/div[2]/div[2]/div/div/div/div[2]/div[4]/div[1]/div[4]/div[" + count + "]")
                    
                    driver.execute_script("arguments[0].scrollIntoView();", holder)
                    log("Holder found")
                    
                    src = holder.find_element(By.TAG_NAME, "shreddit-player")
                    link = src.get_attribute("preview")[0:-11]
                    post_list.append({
                        "link"  : link, 
                        "title" : title,
                        "file"  : link[18:-1] + ".mp4",
                        "upload"  : "upload_" + str(i) + ".mp4",
                    })
                    log("Link found")
                finally:
                    log("Exited: " + str(i))
                log(" ")
        finally:
            log("Terminated driver")
            driver.quit()

        # Use redvid to download posts
        reddit = Downloader(max_q = True)

        log("Downloading list: " + str(len(post_list)))

        i = 0
        for post in post_list:
            reddit.url = post["link"]
            reddit.download()

            time.sleep(2)

            clip = VideoFileClip(post["file"])
            
            # Make sure length is ok
            if clip.duration > 58:
                log("Duration is too long")
                clip = clip.subclip(t_start = 0, t_end = 58)

            # Make sure size is ok
            width, height = clip.size
            if width > height:
                log("Aspect ratio is wrong")
                clip = clip.resize((height, height))
                
            clip.write_videofile("upload_" + str(i) + ".mp4")
            clip.close()
            
            i += 1
                
        log("Done downloading videos")

        # Setup YT service
        API_NAME = "youtube"
        API_VERSION = "v3"
        SCOPES = ["https://www.googleapis.com/auth/youtube"]

        client_file = "client_secrets.json"
        service = create_service(client_file, API_NAME, API_VERSION, SCOPES)
        log("Service created, uploading videos")

        time_div = math.floor(24 / (len(post_list) + 1))
        emojis = " 😀😃😄😁😅😂🤣😊😇🙂🙃😉😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🤩🥳😭😮‍💨😤😠🥶😱😨😰🤗🤔🤭🤫🤥😶😶😐😑😬🙄😯😦😧😮😲🥱😴🤤😪"

        i = 0
        for post in post_list:
            # Create metadata
            random.seed()
            random_emoji = random.randint(0, len(emojis) - 1)
            title = post["title"] + " " + emojis[random_emoji:random_emoji+1]+ emojis[random_emoji:random_emoji+1]
            if len(title) > 99:
                title = title[0:98]
                
            video = post["upload"]

            upload_time = str(datetime.datetime.now().date() + datetime.timedelta(days = 1, hours = 6)) + "T" + str(time_div * i).zfill(2) + ":00:00Z" 
            log("Upload time: " + upload_time)
            
            request_body = {
                "snippet": {
                    "title": title,
                    "description": "#shorts\nI am not the orignal owner to the video.\nIf you are the original owner of the video, and can prove it, I will remove if requested :)\nThis video is allowed under under the U.S. Copyright Office Fair Use Laws",
                    "categoryId": 23,
                    "tags": ["shorts", "ytshorts", "trending", "comedy", "reddit", "safe", "friendly", "love", "youtube", "fun"]
                },
                "status": {
                    "privacyStatus": "private",
                    "publishAt": upload_time,
                    "selfDeclaredMadeForKids": False
                },
                "notifySubscribers": False
            }

            # Upload video
            log("Creating media #" + str(i) + ": " + video + " > " + title)
            media_file = MediaFileUpload(video) 

            log("Uploading media...")
            response_video_upload = service.videos().insert(
                part = "snippet,status",
                body = request_body,
                media_body = media_file
            ).execute()
            uploaded_video_id = response_video_upload.get("id")
            
            log("Media uploaded!")
            media_file.stream().close()
            
            i += 1
            
        time.sleep(1)
            
        i = 0
        for post in post_list:
            video = post["file"]
            log("Deleting " + str(i) + " " + video)
            if os.path.exists(video):
                os.remove(video)
                log("Removed : " + video)
            else:
                log(video + " does not exist!!!") 
            i += 1
            
        i = 0
        for post in post_list:
            video = post["upload"]
            log("Deleting " + str(i) + " " + video)
            if os.path.exists(video):
                os.remove(video)
                log("Removed : " + video)
            else:
                log(video + " does not exist!!!") 
            i += 1
            
        # wait
    log("Waiting...")
    time.sleep(600)
