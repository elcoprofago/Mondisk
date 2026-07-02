import os
import time
import sqlite3
import threading
import queue
import tkinter as tk

DB = "sizes.db"
update_queue = queue.Queue()

# ============================
# 1. Tamaño de carpeta (NO recursivo)
# ============================
def folder_size(path):
    total = 0
    try:
        for f in os.listdir(path):
            fp = os.path.join(path, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    except:
        pass
    return total

# ============================
# 2. Base de datos
# ============================
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sizes (
            path TEXT,
            timestamp INTEGER,
            size INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_measurement(path, size):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO sizes VALUES (?, ?, ?)", (path, int(time.time()), size))
    conn.commit()
    conn.close()

def get_size_hours_ago(path, hours):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cutoff = int(time.time()) - hours * 3600
    cur.execute("""
        SELECT size FROM sizes
        WHERE path=? AND timestamp<=?
        ORDER BY timestamp DESC LIMIT 1
    """, (path, cutoff))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

# ============================
# 3. Monitor (thread)
# ============================
def monitor_root_folders(root_path, hours, threshold_gb, interval_sec):
    print(f"[MONITOR] Escaneando carpetas raíz de: {root_path}")
    print(f"[MONITOR] Umbral: {threshold_gb} GB | Intervalo: {interval_sec} s | Ventana: {hours} h")

    while True:
        changes = []

        try:
            root_dirs = [os.path.join(root_path, d) for d in os.listdir(root_path)]
        except:
            root_dirs = []

        for d in root_dirs:
            if not os.path.isdir(d):
                continue

            current_size = folder_size(d)
            save_measurement(d, current_size)

            previous = get_size_hours_ago(d, hours)
            if previous is None:
                continue

            diff = current_size - previous
            diff_gb = diff / (1024**3)

            if diff_gb >= threshold_gb:
                print(f"[ALERTA] {d} aumentó +{diff_gb:.2f} GB")
                changes.append((d, previous, current_size))

        if changes:
            update_queue.put(changes)

        time.sleep(interval_sec)

# ============================
# 4. GUI estilo consola (Canvas)
# ============================

graph_window = None
canvas = None
rows = {}  # carpeta → y-position
next_y = 10

def draw_row(path, previo, aumento):
    global next_y

    # Si la carpeta ya tiene fila, la actualizamos
    if path in rows:
        y = rows[path]
        # Borrar barra previa
        canvas.create_rectangle(150, y, 150 + 800, y + 18, fill="#222222", outline="")
    else:
        # Crear fila nueva
        y = next_y
        rows[path] = y
        next_y += 40

        # Texto en la misma fila
        canvas.create_text(10, y, anchor="nw", fill="white", text=path)

    # Escala proporcional: 1 px = 10 MB
    scale = 1 / (10 * 1024 * 1024)
    previo_px = int(previo * scale)
    aumento_px = int(aumento * scale)

    bar_h = 18

    # Barra blanca (previo)
    if previo_px > 0:
        canvas.create_rectangle(
            150, y,
            150 + previo_px, y + bar_h,
            fill="white", outline=""
        )

    # Barra roja (aumento)
    if aumento_px > 0:
        canvas.create_rectangle(
            150 + previo_px, y,
            150 + previo_px + aumento_px, y + bar_h,
            fill="red", outline=""
        )

def gui_loop():
    try:
        changes = update_queue.get_nowait()
        for path, old, new in changes:
            draw_row(path, old, new - old)
    except queue.Empty:
        pass

    graph_window.after(300, gui_loop)

# ============================
# 5. Inicio
# ============================
if __name__ == "__main__":
    init_db()

    ROOT = "C:\\"
    HOURS = 0.001
    THRESHOLD_GB = 0.2
    INTERVAL_SEC = 10

    # Ventana principal
    graph_window = tk.Tk()
    graph_window.title("Cambios detectados en directorios")
    graph_window.geometry("600x300")  # tamaño reducido
    graph_window.configure(bg="#222222")
    graph_window.attributes("-topmost", True)

    canvas = tk.Canvas(graph_window, bg="#222222")
    canvas.pack(fill="both", expand=True)

    # Thread del monitor
    t = threading.Thread(
        target=monitor_root_folders,
        args=(ROOT, HOURS, THRESHOLD_GB, INTERVAL_SEC),
        daemon=True
    )
    t.start()

    # Loop GUI
    graph_window.after(300, gui_loop)
    graph_window.mainloop()
