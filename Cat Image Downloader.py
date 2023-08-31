import os
import json
import logging
import requests
from queue import Queue, Empty
from threading import Thread, Lock
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
download_queue = Queue()
gui_queue = Queue()
countdown_label = None
download_button = None
lock = Lock()

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
    global folder_selected, serial_number, download_queue, search_entry, countdown_label
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

    # Start download worker threads
    for _ in range(5):
        t = Thread(target=download_worker)
        t.daemon = True
        t.start()

    # Start GUI update loop
    root.after(100, check_queue, gui_queue)

def download_worker():
    global download_queue, serial_number, lock, gui_queue

    while True:
        url = download_queue.get()
        retries = 3  # Number of retries

        # Retry mechanism
        for i in range(retries):
            try:
                # Attempt to download the image
                response = requests.get(url)
                if response.status_code == 200:
                    with lock:
                        # Log the download and save the image
                        log_to_json_file(serial_number, url, f'image_{serial_number}.jpg')
                        with open(os.path.join(folder_selected, f'image_{serial_number}.jpg'), 'wb') as file:
                            file.write(response.content)
                        gui_queue.put(1)
                        serial_number += 1
                    break  # Exit the retry loop if download is successful
            except Exception as e:
                print(f"Error: {e}. Retrying ({i+1}/{retries})...")
                if i == retries - 1:
                    print("Max retries reached. Stopping script.")
                    return  # Stop the worker thread if max retries reached
            finally:
                download_queue.task_done()

def check_queue(queue):
    try:
        while True:
            item = queue.get_nowait()
            if progress_bar["value"] + item <= progress_bar["maximum"]:
                progress_bar["value"] += item
                countdown_label["text"] = f"Images Remaining: {int(progress_bar['maximum'] - progress_bar['value'])}"
    except Empty:
        pass
    root.after(100, check_queue, queue)



# Initialize Tkinter
root = tk.Tk()
root.title('Image Downloader')

# UI enhancements: using padding and labels
frame = ttk.Frame(root, padding="10")
frame.pack(fill="both", expand=True)

# Add license selection Combobox
license_types = ["All", "Public Domain", "CC0", "CC BY", "CC BY-SA", "CC BY-ND", "CC BY-NC", "CC BY-NC-SA", "CC BY-NC-ND"]
license_combobox = ttk.Combobox(frame, values=license_types)
license_combobox.current(0)  # Default selection
license_combobox.grid(row=0, column=0, pady=5)
license_label = ttk.Label(frame, text="Select License:")
license_label.grid(row=0, column=1, pady=5)

# UI for selecting folder
select_button = ttk.Button(frame, text="Select Folder", command=select_folder)
select_button.grid(row=0, column=0, pady=10)

# UI for entering search query
search_entry = ttk.Entry(frame, width=30)
search_entry.insert(0, "Enter the item to search")
search_entry.bind("<FocusIn>", clear_entry)
search_entry.grid(row=1, column=0, pady=5)

# UI for specifying the number of images
images_entry = ttk.Entry(frame, width=30)
images_entry.insert(0, "Enter the number of images")
images_entry.bind("<FocusIn>", clear_entry)
images_entry.grid(row=2, column=0, pady=5)

# UI for starting the download
download_button = ttk.Button(frame, text="Start Download", command=start_download_thread)
download_button.grid(row=3, column=0, pady=10)

# UI for the progress bar
progress_bar = ttk.Progressbar(frame, orient="horizontal", length=300, mode="determinate")
progress_bar.grid(row=4, column=0, pady=5)

# UI for the remaining images label
countdown_label = ttk.Label(frame, text="")
countdown_label.grid(row=5, column=0)

# Start the Tkinter event loop
root.mainloop()
