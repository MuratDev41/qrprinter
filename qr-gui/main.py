import os
import sys
import requests
import json
import time
import qrcode
import cv2
import threading
from tempfile import gettempdir
from tkinter import Tk, Label, Button, filedialog, simpledialog
from PIL import Image, ImageTk
from escpos.printer import Usb
from pdf2image import convert_from_bytes

# Configuration file
CONFIG_FILE = "printer_config.json"
BACKEND_URL = "http://localhost:5000/files"  # Adjust to match your backend endpoint
BASE_DOWNLOAD_URL = "http://localhost:5000"  # Base URL to download files

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def select_printer(color_type):
    vid = simpledialog.askinteger("Printer Setup", f"Enter USB VID for {color_type} printer")
    pid = simpledialog.askinteger("Printer Setup", f"Enter USB PID for {color_type} printer")
    return {"vid": vid, "pid": pid}

def setup_printers():
    config = {}
    config["black_white"] = select_printer("Black & White")
    config["color"] = select_printer("Color")
    save_config(config)
    return config

def generate_qr(url):
    qr = qrcode.make(url)
    qr.save("qr.png")
    return Image.open("qr.png")

def check_file_color(file_path):
    image = cv2.imread(file_path)
    if image is None:
        return "unknown"
    # Check if image is grayscale or color
    if len(image.shape) == 2 or image.shape[2] == 1:
        return "black_white"
    elif len(image.shape) == 3 and image.shape[2] == 3:
        # Check if all channels are identical (grayscale in color format)
        if (image[:, :, 0] == image[:, :, 1]).all() and (image[:, :, 0] == image[:, :, 2]).all():
            return "black_white"
        else:
            return "color"
    return "unknown"

def print_file(file_path, printer_info):
    try:
        printer = Usb(printer_info["vid"], printer_info["pid"])
        printer.image(file_path)
        printer.cut()
    except Exception as e:
        print(f"Printing error: {e}")

def process_file_content(content, file_extension):
    temp_dir = gettempdir()
    # Save original file
    original_path = os.path.join(temp_dir, f"original_{time.time()}.{file_extension}")
    with open(original_path, "wb") as f:
        f.write(content)
    
    if file_extension.lower() == "pdf":
        # Convert PDF to images
        images = convert_from_bytes(content)
        printed = False
        for i, img in enumerate(images):
            img_path = os.path.join(temp_dir, f"page_{i}.png")
            img.save(img_path, "PNG")
            file_type = check_file_color(img_path)
            printer_info = config.get(file_type)
            if printer_info:
                print_file(img_path, printer_info)
                printed = True
            else:
                print(f"No printer configured for {file_type}")
            os.remove(img_path)
        os.remove(original_path)
        return printed
    else:
        # Check if it's an image
        file_type = check_file_color(original_path)
        printer_info = config.get(file_type)
        if printer_info:
            print_file(original_path, printer_info)
            os.remove(original_path)
            return True
        else:
            print(f"No printer configured for {file_type}")
            os.remove(original_path)
            return False

def listen_for_files():
    config = load_config()
    if not config:
        print("Please configure printers first.")
        return
    
    while True:
        try:
            response = requests.get(BACKEND_URL)
            if response.status_code == 200:
                files = response.json()
                for file_info in files:
                    file_path = file_info.get("path")
                    if not file_path:
                        continue
                    # Download the file
                    download_url = f"{BASE_DOWNLOAD_URL}{file_path}"
                    file_response = requests.get(download_url)
                    if file_response.status_code == 200:
                        file_extension = os.path.splitext(file_path)[1][1:].lower()  # Extract extension without dot
                        if not file_extension:
                            file_extension = "bin"
                        # Process the file content
                        process_file_content(file_response.content, file_extension)
                    else:
                        print(f"Failed to download file from {download_url}")
            else:
                print(f"Failed to fetch files from backend: {response.status_code}")
        except Exception as e:
            print(f"Error in listen_for_files: {e}")
        time.sleep(5)

# GUI Setup
def main():
    global config
    config = load_config()
    if not config:
        config = setup_printers()
    
    root = Tk()
    root.title("QR Printer GUI")
    
    Label(root, text="Scan this QR to upload files").pack()
    img = ImageTk.PhotoImage(generate_qr("http://10.41.50.37:3000/"))
    Label(root, image=img).pack()
    
    Button(root, text="Reconfigure Printers", command=setup_printers).pack()
    
    threading.Thread(target=listen_for_files, daemon=True).start()
    
    root.mainloop()

if __name__ == "__main__":
    main()