import os
import threading
import flickrapi
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

def select_folder():
    global folder_selected
    folder_selected = filedialog.askdirectory()

def start_download():
    global folder_selected

    if not folder_selected:
        messagebox.showinfo("Error", "Please select a folder for downloads.")
        return

    number_of_images = images_entry.get()
    try:
        number_of_images = int(number_of_images)
    except ValueError:
        messagebox.showinfo("Error", "Please enter a valid number for images.")
        return

    select_button.config(state=tk.DISABLED)
    download_button.config(state=tk.DISABLED)

    queue = Queue()
    root.after(100, check_queue, queue)

    thread = threading.Thread(target=download_images, args=(queue, number_of_images))
    thread.start()

def download_images(queue, number_of_images):
    global folder_selected, serial_number

    photos = flickr.photos.search(text='cat', license='1,2,3,4,5,6', per_page=str(number_of_images), page=1)
    total_images = len(photos['photos']['photo'])

    if folder_selected:
        with open(os.path.join(folder_selected, 'image_urls.txt'), 'w') as url_file:
            for i, photo in enumerate(photos['photos']['photo']):
                url = f"https://farm{photo['farm']}.staticflickr.com/{photo['server']}/{photo['id']}_{photo['secret']}.jpg"
                response = requests.get(url)

                url_file.write(f"Serial Number: {serial_number + 1}, URL: {url}\n")

                with open(os.path.join(folder_selected, f'cat_{serial_number}.jpg'), 'wb') as file:
                    file.write(response.content)
                    serial_number += 1

                queue.put(total_images - (i + 1))

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
    except Empty:
        root.after(100, check_queue, queue)

root = tk.Tk()
root.title('Cat Images Downloader')

select_button = tk.Button(root, text="Select Folder", command=select_folder)
select_button.pack(pady=10)

images_entry = tk.Entry(root)
images_entry.pack(pady=10)

download_button = tk.Button(root, text="Start Download", command=start_download)
download_button.pack(pady=10)

countdown_label = tk.Label(root, text="")
countdown_label.pack()

root.mainloop()
