import os
import sys

print("Script started!")
print("Python executable:", sys.executable)
print("Current directory:", os.getcwd())
print("Files in directory:", os.listdir('.'))

import tkinter as tk
root = tk.Tk()
root.withdraw()
print("GUI initialized")

root.after(5000, root.destroy)
root.mainloop()
print("Script completed!")