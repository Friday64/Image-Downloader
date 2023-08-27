import os
import threading
import flickrapi
from flickrapi import FlickrAPI, FlickrError
import requests
import logging
import tkinter as tk
from tkinter import filedialog
import tkinter.messagebox as messagebox
from queue import Queue, Empty
from dotenv import load_dotenv as ld_dotenv

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler
file_handler = logging.FileHandler('cat_image_downloader.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s: %(message)s'))
logger.addHandler(file_handler)

# Load .env file containing Flickr API keys
ld_dotenv(os.path.join(os.path.expanduser("~"), 'Desktop/.env'))

# Flickr API setup
FLICKR_API_KEY = str(os.getenv('FLICKR_API_KEY'))
API_SECRET = str(os.getenv('FLICKR_API_SECRET'))

# Create an instance of the flickrapi module
flickr = flickrapi.FlickrAPI(FLICKR_API_KEY, API_SECRET, format='parsed-json')
serial_number = 0  # Initialize a global serial number counter
folder_selected = ""  # Store the selected folder path
queue = Queue()  # Define queue at a global scope


def select_folder():
    global folder_selected
    folder_selected = filedialog.askdirectory()

def start_download():
    global folder_selected, serial_number

    serial_number = get_starting_serial_number()

    serial_number = get_starting_serial_number()
    images_per_page = 500
    pages_needed = (number_of_images + images_per_page - 1) // images_per_page
    remaining_images = number_of_images
    
    if folder_selected:
        for page in range(pages_needed):
            images_to_fetch = min(remaining_images, images_per_page)
            number_of_images = images_entry.get()
            try:
                photos = flickr.photos.search(
                    text='cat',
                    license='1,2,3,4,5,6',
                    per_page=str(images_to_fetch),
                    page=page + 1
                )
            except FlickrError as e:
                logger.error(f"Flickr API Error: {e}")
                return

            total_images = len(photos['photos']['photo'])

            with open(os.path.join(folder_selected, 'image_urls.txt'), 'a') as url_file:
                for i, photo in enumerate(photos['photos']['photo']):
                    try:
                        url = f"https://farm{photo['farm']}.staticflickr.com/{photo['server']}/{photo['id']}_{photo['secret']}.jpg"
                        response = requests.get(url)
                        if response.status_code != 200:
                            logger.warning(f"Failed to download image from URL: {url}")
                            continue

                        url_file.write(f"Serial Number: {serial_number}, URL: {url}\n")

                        with open(os.path.join(folder_selected, f'cat_{serial_number}.jpg'), 'wb') as file:
                            file.write(response.content)
                            serial_number += 1

                        queue.put(number_of_images - (page * images_per_page + i + 1))
                        remaining_images -= 1

                        if serial_number >= 100:  # Add download limit of 100 images
                            logger.info("Download limit of 100 images reached.")
                            queue.put(-1)
                            return

                    except requests.exceptions.RequestException as e:
                        logger.error(f"Network Error: {e}")

        logger.info("Download finished!")
        queue.put(-1)


def check_queue(queue):
    try:
        remaining_images = queue.get_nowait()
        if remaining_images >= 0:
            countdown_label.config(text=f"Images Remaining: {remaining_images}")
            root.after(100, check_queue, queue)
        else:
            countdown_label.config(text="")
            select_button.config(state=tk.NORMAL)
            download_button.config(state=tk.NORMAL)
            num_images_label.config(text="")
    except Empty:
        root.after(100, check_queue, queue)

def get_starting_serial_number():
    global folder_selected
    url_file_path = os.path.join(folder_selected, 'image_urls.txt')
    last_serial_number = 0

    if os.path.exists(url_file_path):
        with open(url_file_path, 'r') as url_file:
            lines = url_file.readlines()
            if lines:
                last_line = lines[-1]
                try:
                    last_serial_number = int(last_line.split(",")[0].split(":")[1].strip())
                except ValueError:
                    pass

    return last_serial_number + 1



root = tk.Tk()
root.title('Cat Images Downloader')

select_button = tk.Button(root, text="Select Folder", command=select_folder)
select_button.pack(pady=10)

images_entry = tk.Entry(root)
images_entry.pack(pady=5)

num_images_label = tk.Label(root, text="")
num_images_label.pack()

download_button = tk.Button(root, text="Start Download", command=start_download)
download_button.pack(pady=10)

countdown_label = tk.Label(root, text="")
countdown_label.pack()

root.mainloop()
