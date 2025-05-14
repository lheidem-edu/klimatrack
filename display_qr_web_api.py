#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filepath: /home/lheidem/klimatrack/display_qr_web_api.py

import socket
import time
import qrcode
from PIL import Image, ImageDraw, ImageFont
import subprocess
import netifaces

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
I2C_PORT = 1
I2C_ADDRESS = 0x3C

def get_ip_address():
    """
    Get the Raspberry Pi's current IP address from either ethernet or WLAN interface.
    Returns the IP as string or None if no connection is available.
    """
    interfaces = ['eth0', 'wlan0']
    
    for interface in interfaces:
        try:
            if interface in netifaces.interfaces():
                addresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addresses:
                    ip_info = addresses[netifaces.AF_INET][0]
                    ip_address = ip_info['addr']
                    if not ip_address.startswith('127.'):
                        return interface, ip_address
        except:
            continue
    
    return None, None

def create_qr_code(data, size=None, target_width=None, target_height=None):
    """
    Create a QR code image for the given data.
    If target dimensions are provided, attempts to optimize the QR code size.
    """
    version = 1
    border = 1
    
    if size is None and target_width is not None and target_height is not None:
        min_dimension = min(target_width, target_height)
        
        data_length = len(data)
        if data_length > 40:
            version = 2
        if data_length > 80:
            version = 3
        
        modules = 4 * version + 17 + (border * 2)
        box_size = min_dimension // modules
        
        size = max(1, box_size)
    
    if size is None:
        size = 1
    
    qr = qrcode.QRCode(
        version=version,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="white", back_color="black")
    
    img = img.convert("RGB").convert("1")
    
    return img

def render_display(device, interface, ip_address):
    """
    Render the display with a full-screen QR code.
    """
    url = f"http://{ip_address}:8080/"
    qr_img = create_qr_code(url, target_width=DISPLAY_WIDTH, target_height=DISPLAY_HEIGHT)
    
    qr_width, qr_height = qr_img.size
    x_pos = (DISPLAY_WIDTH - qr_width) // 2
    y_pos = (DISPLAY_HEIGHT - qr_height) // 2
    
    with canvas(device) as draw:
        try:
            draw.bitmap((x_pos, y_pos), qr_img, fill="white")
        except Exception as e:
            print(f"Error rendering QR code: {e}")
            font = ImageFont.load_default()
            draw.text((0, 0), "QR Error", font=font, fill="white")

def main():
    """
    Main function to initialize display and show the QR code.
    """
    try:
        serial = i2c(port=I2C_PORT, address=I2C_ADDRESS)
        device = ssd1306(serial, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
        
        print("OLED display initialized")
        
        while True:
            interface, ip_address = get_ip_address()
            
            if ip_address:
                print(f"Displaying QR code for {interface} IP: {ip_address}")
                render_display(device, interface, ip_address)
            else:
                with canvas(device) as draw:
                    font = ImageFont.load_default()
                    draw.text((10, 20), "No network", font=font, fill="white")
                    draw.text((10, 35), "connection found", font=font, fill="white")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("Program terminated by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
