print("Testing...")
import tkinter as tk
root = tk.Tk()
root.withdraw()
print("GUI created")
root.after(1000, root.destroy)
root.mainloop()
print("Done")