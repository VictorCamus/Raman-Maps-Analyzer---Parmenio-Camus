import tkinter as tk
from tkinter import ttk

root = tk.Tk()

nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True)

for i in range(5):
    frame = ttk.Frame(nb)
    nb.add(frame, text=f"Tab {i}")

drag_tab = None

def on_press(event):
    global drag_tab
    try:
        drag_tab = nb.index(f"@{event.x},{event.y}")
    except tk.TclError:
        drag_tab = None

def on_drag(event):
    global drag_tab
    if drag_tab is None:
        return

    try:
        target = nb.index(f"@{event.x},{event.y}")
    except tk.TclError:
        return

    if target != drag_tab:
        nb.insert(target, drag_tab)
        drag_tab = target

nb.bind("<ButtonPress-1>", on_press)
nb.bind("<B1-Motion>", on_drag)

root.mainloop()