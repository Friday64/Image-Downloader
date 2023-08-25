import tkinter as tk
from tkinter import ttk

def start_download():
    print("Download started...")

root = tk.Tk()
root.title('Cat Images Downloader')

folder_button = tk.Button(root, text="Start Download", command=start_download)
folder_button.pack(pady=10)

root.mainloop()
