import time
import datetime
import pickle
import os
os.environ["IMAGEIO_FFMPEG_EXE"] = "C:\\FFmpeg\\bin\\ffmpeg.exe"
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

### Setup stufff
def log(str):
    print("[Scraper] " + str)
    time.sleep(0.75)
def clamp(num, min_value, max_value):
   return max(min(num, max_value), min_value)

### Create loop
last_day = None

while True:
    today = datetime.datetime.now().date()
    if today != last_day:
        last_day = today
        # BEGIN!!!
        post_list = []
        
        options = Options()
        options.add_experimental_option("detach", True)
        driver = webdriver.Chrome(
            service = Service(ChromeDriverManager().install()),
            options = options
        )

        reddit = Downloader(max_q = True)
        videos_per = 1
        links = [
            "https://www.reddit.com/r/Damnthatsinteresting/",
            "https://www.reddit.com/r/BeAmazed/",
            "https://www.reddit.com/r/nextfuckinglevel/"
        ]

        ### Begin scraping reddit links ^^^
        xpath = "/html/body/div[1]/div/div[2]/div[2]/div/div/div/div[2]/div[4]/div[1]/div[4]"
        for j in range(len(links)):
            curr_link = links[j]
            
            driver.get(curr_link + "top/?t=day")
            body = None
            while body == None:
                try:
                    body = WebDriverWait(driver, 20).until(
                        Ec.presence_of_element_located((By.CLASS_NAME, "rpBJOHq2PR60pnwJlUyP0"))
                    )
                except:
                    driver.refresh()
                    time.sleep(10)
                
            log("Found body in " + str(j) + ": " + curr_link)
            
            i = 0
            vids = 0
            while vids < videos_per:
                log("Searching " + str(i) + "...")
                
                count = str(i + 2)
                stub = "/div[" + count + "]/div/div"
                
                post = driver.find_element(By.XPATH, xpath + stub)
                driver.execute_script("arguments[0].scrollIntoView();", post)
                log("Found post.")
                
                post_id = post.get_attribute("id")
                if len(post_id) == 0:
                    log("Post is an Ad.")
                elif len(post_id) > 100:
                    log("Post is something wack.")
                else:
                    log("Post checkable!")
                    try:
                        link, title_dir = None, None
                        try:
                            link = driver.find_element(By.XPATH, xpath + stub + "/div[3]/div[2]/div[2]/a")
                            title_dir = "/div[3]/div[2]/div[2]/a/div/h3"
                            log("Post has a Tag.")
                        except:
                            link = driver.find_element(By.XPATH, xpath + stub + "/div[3]/div[2]/div[1]/a")
                            title_dir = "/div[3]/div[2]/div[1]/a/div/h3"
                            log("Post has NO Tag.")
            
                        reddit.url = link.get_attribute("href")
                        try:
                            num = str(len(post_list))
                            name = "download_" + num + ".mp4"
                            
                            # cheeky redvid name override :)
                            reddit.download(name)   
                        except:
                            log("Failed! Wrong post type...")
                            
                        if os.path.exists(name):
                            log("Video extracted!")
                            
                            title = driver.find_element(By.XPATH, xpath + stub + title_dir)
                            post_list.append({
                                "title": title.text,
                                "download": name,
                                "upload": "upload_" + num + ".mp4",
                            })
                            
                            vids += 1
                        else:
                            log("Failed! Video could not download!")
                    except:
                        log("Something wacky happened")
                        
                i += 1
            log(" ")
        log(" ")
        driver.quit()

        ### Edit scraped videos
        log("Begin edit")
        for i in range(len(post_list)):
            log("Clip " + str(i) + "...")
            post = post_list[i]
            clip = VideoFileClip(post["download"])
            
            # Make sure length is ok
            if clip.duration > 58:
                log("Duration is too long! Fixing...")
                clip = clip.subclip(t_start = 0, t_end = 58)

            # Make sure resolution is ok
            width, height = clip.size
            if width > height:
                log("Aspect ratio is wrong! Fixing...")
                clip = clip.resize((height, height))
                
            clip.write_videofile("upload_" + str(i) + ".mp4")
            clip.close()
            
            log("Clip edited.")
        log("Done editing videos")
        log(" ")

        # Setup YT service
        service = None
        CLIENT_SECRET_FILE = "cfg/client_secrets.json"
        API_SERVICE_NAME = "youtube"
        API_VERSION = "v3"
        SCOPES = ["https://www.googleapis.com/auth/youtube"]

        cred = None
        pickle_file = f"cfg/token_{API_SERVICE_NAME}_{API_VERSION}.pickle"

        if os.path.exists(pickle_file):
            with open(pickle_file, "rb") as token:
                cred = pickle.load(token)

        if not cred or not cred.valid:
            if cred and cred.expired and cred.refresh_token:
                os.remove(pickle_file)
            
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()

            with open(pickle_file, "wb") as token:
                pickle.dump(cred, token)

        try:
            service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        except Exception as e:
            print("!!Unable to connect!!")
            print(e)

        if service != None:
            log("YT service found, uploading videos")

            time_div = math.floor(24 / (len(post_list) + 1))
            emojis = "🔴🟠🟡🟢🔵🟣🟤⚫⚪🟥🟧🟨🟩🟦🟪🟫⬛⬜"

            i = 0
            for post in post_list:
                # Create metadata
                random.seed()
                random_emoji = random.randint(0, len(emojis) - 1)
                title = post["title"] + " " + emojis[random_emoji:random_emoji + 1] + emojis[random_emoji:random_emoji + 1] + "!!"
                video = post["upload"]

                upload_time = str(datetime.datetime.now().date() + datetime.timedelta(days = 1, hours = clamp(7 + random.randint(-1, 1), 0, 24))) + "T" + str(time_div * i).zfill(2) + ":00:00Z" 
                log("Upload time: " + upload_time)
                
                request_body = {
                    "snippet": {
                        "title": title if len(title) < 99 else title[0:98],
                        "description": title + " #shorts #ytshorts #youtube #trending",
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
        else:
            log("No YT service found")

        for post in post_list:
            upload = post["upload"]
            log("Deleting " + upload)
            if os.path.exists(upload):
                os.remove(upload)
                log("Removed : " + upload)
            else:
                log(upload + " does not exist!!!") 
                
            download = post["download"]
            log("Deleting " + download)
            if os.path.exists(download):
                os.remove(download)
                log("Removed : " + download)
            else:
                log(download + " does not exist!!!")

        log("Terminated.")
        
    log("Waiting...")
    time.sleep(600)
