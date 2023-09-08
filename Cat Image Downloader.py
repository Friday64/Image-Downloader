import os
from datetime import datetime
from dotenv import load_dotenv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from queue import Queue, Empty
from flickrapi import FlickrAPI, FlickrError
import requests
from concurrent.futures import ThreadPoolExecutor
import threading
import json

# Specify your custom path here
custom_path = 'C:/Users/Matthew/Desktop/Cat-Image-Downloader-V1/.env'
load_dotenv(dotenv_path=custom_path)

FLICKR_API_KEY = str(os.getenv('FLICKR_PUBLIC_API_KEY'))
FLICKR_API_SECRET = str(os.getenv('FLICKR_SECRET_API_KEY'))

if not FLICKR_API_KEY or not FLICKR_API_SECRET:
    raise ValueError("API keys are not defined. Please check your .env file and the custom path.")

root = tk.Tk()
root.title("Flickr Image Downloader")

def validate_api_keys():
    try:
        flickr = FlickrAPI(FLICKR_API_KEY, FLICKR_API_SECRET, format='parsed-json')
        flickr.test.echo()  # Use test.echo to validate API keys.
    except FlickrError as e:
        if '100' in str(e):
            messagebox.showerror("Invalid API Key", "The API key format is invalid.")
            root.quit()
        else:
            messagebox.showerror("API Error", str(e))
            root.quit()
    except Exception as e:
        messagebox.showerror("Unexpected Error", str(e))
        root.quit()

validate_api_keys()

MAX_WORKERS = 10

download_queue = Queue()
gui_queue = Queue()

folder_selected = None

executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

def set_folder():
    global folder_selected
    folder_selected = filedialog.askdirectory()
    folder_label.config(text=folder_selected)

metadata_lock = threading.Lock()

def save_metadata(search_term, photo, file_name):
    print(f"Debug: Photo Data: {photo}")  # Debug line to print photo data to the console
    
    metadata = {
        "url": f"https://www.flickr.com/photos/{photo['owner']}/{photo['id']}",
        "name": file_name,
        "creator": photo.get('ownername', 'Unknown Creator'),  # Default value added
        "license": photo.get('license', 'Unknown License'),  # Default value added
    }

    metadata_path = os.path.join(folder_selected, "metadata.json")
    
    with metadata_lock:
        try:
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as file:
                    existing_data = json.load(file)
                existing_data.append(metadata)
                with open(metadata_path, 'w') as file:
                    json.dump(existing_data, file, indent=4)
            else:
                with open(metadata_path, 'w') as file:
                    json.dump([metadata], file, indent=4)
            print(f"Metadata for {file_name} saved successfully")
        except Exception as e:
            print(f"An error occurred while saving metadata for {file_name}: {e}")

def download_images_from_flickr():
    search_term = search_entry.get()
    num_of_images = int(images_entry.get())

    if not folder_selected:
        messagebox.showwarning("Folder Not Selected", "Please select a folder to save the images.")
        return

    if not search_term:
        messagebox.showwarning("Search Term Not Provided", "Please provide a search term.")
        return

    if not num_of_images:
        messagebox.showwarning("Number of Images Not Provided", "Please provide the number of images to download.")
        return

    # Reset progress bar
    progress_bar['value'] = 0
    countdown_label.config(text="Images Remaining: 0")

    flickr = FlickrAPI(FLICKR_API_KEY, FLICKR_API_SECRET, format='parsed-json')
    photos = flickr.photos.search(
        text=search_term, per_page=num_of_images, page=1, sort='relevance',
        license='1,2,3,4,5,6',  # Creative Commons licenses
        content_type=1,  # Only photos
        extras='owner_name,license'  # Attempt to fetch owner_name and license info
    )
    
    if photos and photos['photos']['photo']:
        photos_list = photos['photos']['photo']

        for photo in photos_list:
            url = f"https://live.staticflickr.com/{photo['server']}/{photo['id']}_{photo['secret']}_c.jpg"
            download_queue.put((url, search_term, photo))

        countdown_label.config(
            text=f"Images Remaining: {download_queue.qsize()}")

        # Reset progress bar maximum value
        progress_bar['maximum'] = download_queue.qsize()

        for i in range(MAX_WORKERS):
            executor.submit(download_image)

    else:
        messagebox.showinfo("No Images Found", "No images found for the provided search term.")

def download_image():
    while not download_queue.empty():
        try:
            url, search_term, photo = download_queue.get_nowait()
        except Empty:
            break
        else:
            response = requests.get(url)
            if response.status_code == 200:
                file_name = create_file_name(search_term, photo)

                save_image(response.content, file_name)
                save_metadata(search_term, photo, file_name)
            gui_queue.put(None)
            download_queue.task_done()

def create_file_name(search_term, photo):
    timestamp = datetime.now().strftime('%m_%d_%Y')
    return f"{search_term}_{timestamp}_{photo['id']}.jpg"


def save_image(content, file_name):
    if folder_selected:
        image_path = os.path.join(folder_selected, file_name)
        with open(image_path, "wb") as file:
            file.write(content)

def check_gui_queue():
    while True:
        try:
            _ = gui_queue.get_nowait()
        except Empty:
            break
        else:
            progress_bar['value'] += 1
            remaining = download_queue.qsize()
            countdown_label.config(text=f"Images Remaining: {remaining}")
            if remaining == 0:
                countdown_label.config(text="All images downloaded!")
    root.after(100, check_gui_queue)
    
# UI Setup
search_label = ttk.Label(root, text="Search Term:")
search_label.grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)

search_entry = ttk.Entry(root, width=40)
search_entry.grid(column=1, row=0, sticky=tk.W, padx=5, pady=5)

images_label = ttk.Label(root, text="Number of Images:")
images_label.grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)

images_entry = ttk.Entry(root, width=40)
images_entry.grid(column=1, row=1, sticky=tk.W, padx=5, pady=5)

folder_btn = ttk.Button(root, text="Select Folder", command=set_folder)
folder_btn.grid(column=0, row=2, sticky=tk.W, padx=5, pady=5)

folder_label = ttk.Label(root, text="")
folder_label.grid(column=1, row=2, sticky=tk.W, padx=5, pady=5)

download_btn = ttk.Button(root, text="Download", command=download_images_from_flickr)
download_btn.grid(column=1, row=3, sticky=tk.W, padx=5, pady=20)

progress_bar = ttk.Progressbar(root, orient='horizontal', length=300, mode='determinate')
progress_bar.grid(column=1, row=4, sticky=tk.W, padx=5, pady=5)

countdown_label = ttk.Label(root, text="")
countdown_label.grid(column=1, row=5, sticky=tk.W, padx=5, pady=5)

root.after(100, check_gui_queue)

root.mainloop()
