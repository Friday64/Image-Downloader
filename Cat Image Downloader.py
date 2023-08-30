import os
import json
import logging
import requests
from queue import Queue, Empty
from threading import Thread
from flickrapi import FlickrAPI, FlickrError
from dotenv import find_dotenv, load_dotenv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Initialize Global Variables
progress_bar = None
images_entry = None
search_entry = None
folder_selected = ""
serial_number = 0
queue = Queue()
countdown_label = None
download_button = None

# Initialize Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('image_downloader.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s: %(message)s'))
logger.addHandler(file_handler)

# Load Environment Variables from .env file
dotenv_path = ""  # Fill in the path to your .env file here
load_dotenv(dotenv_path)
FLICKR_API_KEY = str(os.getenv('FLICKR_API_KEY'))
FLICKR_API_SECRET = str(os.getenv('FLICKR_API_SECRET'))
flickr = FlickrAPI(FLICKR_API_KEY, FLICKR_API_SECRET, format='parsed-json')

def select_folder():
    global folder_selected
    folder_selected = filedialog.askdirectory()

def log_to_json_file(serial_number, url, photo_name):
    json_file_path = os.path.join(folder_selected, 'image_log.json')
    image_records = []
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as json_file:
            image_records = json.load(json_file)
    image_detail = {
        "Serial_Number": serial_number,
        "URL": url,
        "Photo_Name": photo_name
    }
    image_records.append(image_detail)
    with open(json_file_path, 'w') as json_file:
        json.dump(image_records, json_file, indent=4)

def get_starting_serial_number():
    global folder_selected
    json_file_path = os.path.join(folder_selected, 'image_log.json')
    last_serial_number = 0
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as json_file:
            image_records = json.load(json_file)
            if image_records:
                last_record = image_records[-1]
                last_serial_number = last_record["Serial_Number"]
    return last_serial_number + 1

def start_download_thread():
    thread = Thread(target=start_download)
    thread.start()

def start_download():
    global folder_selected, serial_number, progress_bar, queue, search_entry
    if not folder_selected:
        messagebox.showerror("Error", "Please select a folder.")
        return

    search_item = search_entry.get()
        
    serial_number = get_starting_serial_number()
    number_of_images = int(images_entry.get())
    progress_bar["maximum"] = number_of_images
    
    # Rest of the logic to download images stays the same
    # Just change the 'text' parameter in flickr.photos.search to the value of search_item

# Initialize Tkinter
root = tk.Tk()
root.title('Image Downloader')

select_button = tk.Button(root, text="Select Folder", command=select_folder)
select_button.pack(pady=10)

search_entry = tk.Entry(root, width=30)
search_entry.insert(0, "Enter the item to search")
search_entry.pack(pady=5)

images_entry = tk.Entry(root, width=30)
images_entry.insert(0, "Enter the number of images")
images_entry.pack(pady=5)

download_button = tk.Button(root, text="Start Download", command=start_download_thread)
download_button.pack(pady=10)

progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.pack(pady=5)

countdown_label = tk.Label(root, text="")
countdown_label.pack()

root.mainloop()
