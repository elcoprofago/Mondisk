#!/usr/bin/env python3
import os
import sys
import time
import threading
import tkinter as tk

# Test if console output works
print("=== Script started ===")

# Test config reading
import configparser
config = configparser.ConfigParser()
config.read("config.ini")
MOSTRAR_CONSOLA = config["VENTANA"]["mostrar_consola"].split()[0].lower() == "si"
print(f"MOSTRAR_CONSOLA: {MOSTRAR_CONSOLA}")

if not MOSTRAR_CONSOLA:
    print("Redirecting stdout to null")
    sys.stdout = open(os.devnull, "w")

# Test GUI creation
print("Creating GUI...")
root = tk.Tk()
try:
    root.iconphoto(False, tk.PhotoImage(file="icon.ico"))
    print("Icon loaded")
except Exception as e:
    print(f"Icon error (ignored): {e}")

root.withdraw()
print("GUI created and hidden")

# Test monitor thread
class DummyGUI:
    def __init__(self):
        pass

def test_monitor():
    print("Monitor thread started")
    for i in range(3):
        print(f"Monitor iteration {i}")
        time.sleep(1)
    print("Monitor thread finished")

gui = DummyGUI()
monitor_thread = threading.Thread(target=test_monitor, daemon=True)
monitor_thread.start()

print("Starting mainloop...")
root.after(5000, root.destroy)
root.mainloop()
print("Script completed")