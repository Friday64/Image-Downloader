from inspect import FrameInfo
import os
import json
import logging
from pickle import FRAME
from queue import Empty, Queue
from threading import Lock
from traceback import FrameSummary
from types import FrameType
from flickrapi import FlickrAPI, FlickrError
from dotenv import load_dotenv
import tkinter as tk
from tkinter import Frame, ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor
from time import sleep
import requests
 

# Initialize Global Variables
progress_bar = None
images_entry = None
search_entry = None
folder_selected = ""
serial_number = 0
download_queue = Queue()
gui_queue = Queue()
countdown_label = None
download_button = None
lock = Lock()
failed_urls = []

# Initialize Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('image_downloader.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s: %(message)s'))
logger.addHandler(file_handler)

# Load Environment Variables
dotenv_path = "C:/Users/Matthew/Desktop/Cat-Image-Downloader-V1/.env"  # Fill in the path to your .env file
load_dotenv(dotenv_path)
FLICKR_API_KEY = str(os.getenv('FLICKR_API_KEY'))
FLICKR_API_SECRET = str(os.getenv('FLICKR_API_SECRET'))
flickr = FlickrAPI(FLICKR_API_KEY, FLICKR_API_SECRET, format='parsed-json')

def clear_entry(event):
    event.widget.delete(0, tk.END)

def select_folder():
    global folder_selected
    folder_selected = filedialog.askdirectory()

# Modified log_to_json_file to add better error handling
def log_to_json_file(serial_number, url, photo_name):
    try:
        json_file_path = os.path.join(folder_selected, 'image_log.json')
        if not json_file_path:
            raise ValueError("No folder selected")
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
    except Exception as e:
        logger.error(f"Error writing to JSON file: {e}")


def get_starting_serial_number():
    global folder_selected
    last_serial_number = 0
    try:
        return int(last_serial_number) + 1
    except ValueError:
        print("Error: last_serial_number is not a valid integer.")
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
    global folder_selected, serial_number, download_queue, search_entry, countdown_label, root
    if not folder_selected:
        messagebox.showerror("Error", "Please select a folder.")
        return

    search_item = search_entry.get()

    serial_number = get_starting_serial_number()
    number_of_images = int(images_entry.get())
    progress_bar["maximum"] = number_of_images
    download_queue.queue.clear()
    countdown_label["text"] = f"Images Remaining: {number_of_images}"

    # Fetch URLs and populate download queue
    try:
        photos = flickr.photos.search(
            text=search_item,
            license='1,2,3,4,5,6',
            per_page=str(number_of_images)
        )
    except FlickrError as e:
        logger.error(f"Flickr API Error: {e}")
        print(f"Flickr API Error: {e}")
        return

    for photo in photos['photos']['photo']:
        url = f"https://farm{photo['farm']}.staticflickr.com/{photo['server']}/{photo['id']}_{photo['secret']}.jpg"
        download_queue.put(url)

    # Initialize worker threads using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        for _ in range(5):
            executor.submit(download_worker)

    # Start GUI update loop
    root.after(100, check_queue, gui_queue)
def check_queue(queue):
    try:
        while True:
            item = queue.get_nowait()
            if progress_bar["value"] + item <= progress_bar["maximum"]:
                progress_bar["value"] += item
                remaining_images = int(progress_bar['maximum'] - progress_bar['value'])
                countdown_label["text"] = f"Images Remaining: {remaining_images}"

                # Reset the progress bar and remaining images when download is complete
                if remaining_images == 0:
                    progress_bar["value"] = 0
                    countdown_label["text"] = "Download complete. Progress bar reset."
                    
    except Empty:
        pass
    root.after(100, check_queue, queue)
def download_worker():
    global download_queue, serial_number, lock, gui_queue
    while True:
        url = download_queue.get()
        
        retries = 3  # Number of retries
        delay = 3   # Delay between retries in seconds
        success = False  # Flag to indicate if the download was successful
        
        for i in range(retries):
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
                response = requests.get(url, timeout=10, headers=headers)
                
                if response.status_code == 200:
                    with lock:
                        log_to_json_file(str(serial_number), url, f'image_{serial_number}.jpg')
                        with open(os.path.join(folder_selected, f'image_{serial_number}.jpg'), 'wb') as file:
                            file.write(response.content)
                        gui_queue.put(1)
                        serial_number += 1
                    success = True
                    break
            except requests.exceptions.RequestException as e:
                print(f"An error occurred: {e}. Retrying {i+1}/{retries}")
                sleep(delay)  # Adding delay between retries
                #delay *= 2  # Exponential back-off
        
        if not success:
            print("Max retries reached. Skipping this URL.")
            failed_urls.append(url)  # Append failed URL for later inspection
            
        download_queue.task_done()

root = tk.Tk()
root.title('Image Downloader')

# Create a single frame for all widgets
frame = ttk.Frame(root, padding="20")
frame.pack(fill="both", expand=True)

# UI for license selection Combobox
ttk.Label(frame, text="Select License:").grid(row=0, column=0, pady=10)
license_types = ["All", "Public Domain", "CC0", "CC BY", "CC BY-SA", "CC BY-ND", "CC BY-NC", "CC BY-NC-SA", "CC BY-NC-ND"]
license_combobox = ttk.Combobox(frame, values=license_types)
license_combobox.grid(row=0, column=1, pady=10)

# UI for specifying the number of images
ttk.Label(frame, text="Number of Images:").grid(row=1, column=0, pady=10)
images_entry = ttk.Entry(frame, width=30)
images_entry.insert(0, "Enter the number of images")
images_entry.bind("<FocusIn>", clear_entry)
images_entry.grid(row=1, column=1, pady=10)

# UI for entering search query
ttk.Label(frame, text="Search Query:").grid(row=2, column=0, pady=10)
search_entry = ttk.Entry(frame, width=30)
search_entry.insert(0, "Enter the item to search")
search_entry.bind("<FocusIn>", clear_entry)
search_entry.grid(row=2, column=1, pady=10)

# UI for starting the download
download_button = ttk.Button(frame, text="Start Download", command=start_download_thread)
download_button.grid(row=3, column=1, pady=10)

# UI for the progress bar
progress_bar = ttk.Progressbar(frame, orient="horizontal", length=300, mode="determinate")
progress_bar.grid(row=4, column=0, columnspan=2, pady=10)

# UI for the remaining images label
countdown_label = ttk.Label(frame, text="")
countdown_label.grid(row=5, column=0, columnspan=2, pady=10)

# UI for folder selection
select_folder_button = ttk.Button(frame, text="Select Folder", command=select_folder)
select_folder_button.grid(row=6, column=1, pady=10)

# Start the Tkinter event loop
root.mainloop()





