import os
import time
import threading
import tkinter as tk

# ============================
# CONFIGURACIÓN
# ============================
GB = 1024 * 1024 * 1024
MAX_GB = 10
BAR_HEIGHT = 18
MAX_BAR = 300

COLOR_NO_CHANGE = "white"
COLOR_INCREASE = "cyan"
COLOR_DECREASE = "lime"

BG = "#000084"   # Color de fondo pedido

# ============================
# 1. Tamaño de carpeta (RECURSIVO)
# ============================
def folder_size(path):
    total = 0
    for root, dirs, files in os.walk(path, topdown=True, onerror=lambda e: None):
        for f in files:
            try:
                fp = os.path.join(root, f)
                total += os.path.getsize(fp)
            except:
                pass
    return total

# ============================
# 3. GUI
# ============================
class MonitorGUI:
    def __init__(self, root):
        self.root = root
        self.window = None
        self.rows = {}

    def create_window(self):
        if self.window is not None:
            return

        # Ventana sin título
        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)
        self.window.configure(bg=BG)
        self.window.geometry("420x300")

        # Fondo redondeado
        self.bg = tk.Canvas(self.window, bg=BG, highlightthickness=0)
        self.bg.pack(fill="both", expand=True)

        w, h, r = 420, 300, 20

        self.bg.create_arc((0, 0, r*2, r*2), start=90, extent=90, fill=BG, outline=BG)
        self.bg.create_arc((w-r*2, 0, w, r*2), start=0, extent=90, fill=BG, outline=BG)
        self.bg.create_arc((0, h-r*2, r*2, h), start=180, extent=90, fill=BG, outline=BG)
        self.bg.create_arc((w-r*2, h-r*2, w, h), start=270, extent=90, fill=BG, outline=BG)
        self.bg.create_rectangle(r, 0, w-r, h, fill=BG, outline=BG)
        self.bg.create_rectangle(0, r, w, h-r, fill=BG, outline=BG)

        # ============================
        # Botón de cierre ✕
        # ============================
        self.close_btn = tk.Label(
            self.window,
            text="✕",
            fg="white",
            bg="#444444",
            font=("Consolas", 12),
            padx=5,
            pady=2
        )
        self.close_btn.place(x=w-30, y=10)
        self.close_btn.place_forget()

        def close_app(event=None):
            self.window.destroy()

        self.close_btn.bind("<Button-1>", close_app)

        # ============================
        # Botón minimizar _
        # ============================
        self.min_btn = tk.Label(
            self.window,
            text="_",
            fg="white",
            bg="#444444",
            font=("Consolas", 12),
            padx=5,
            pady=2
        )
        self.min_btn.place(x=w-60, y=10)
        self.min_btn.place_forget()

        def minimize_app(event=None):
            self.window.iconify()

        self.min_btn.bind("<Button-1>", minimize_app)

        # ============================
        # Mostrar/ocultar botones
        # ============================
        def show_buttons(event):
            self.close_btn.place(x=w-30, y=10)
            self.min_btn.place(x=w-60, y=10)

        def hide_buttons(event):
            self.close_btn.place_forget()
            self.min_btn.place_forget()

        self.window.bind("<Enter>", show_buttons)
        self.window.bind("<Leave>", hide_buttons)

        # ============================
        # Mover ventana con botón derecho
        # ============================
        def start_move(event):
            self._drag_x = event.x
            self._drag_y = event.y

        def do_move(event):
            x = self.window.winfo_x() + (event.x - self._drag_x)
            y = self.window.winfo_y() + (event.y - self._drag_y)
            self.window.geometry(f"+{x}+{y}")

        self.window.bind("<Button-3>", start_move)
        self.window.bind("<B3-Motion>", do_move)

        # Contenedor
        self.container = tk.Frame(self.window, bg=BG)
        self.container.place(x=10, y=40)

    def draw_row(self, path, previo, actual):
        self.create_window()

        aumento = actual - previo
        total = previo + aumento

        # Escala fija: 10 GB = MAX_BAR px
        if total > 0:
            previo_pct = previo / (MAX_GB * GB)
            aumento_pct = aumento / (MAX_GB * GB)
            if previo_pct + aumento_pct > 1:
                factor = 1 / (previo_pct + aumento_pct)
                previo_pct *= factor
                aumento_pct *= factor
        else:
            previo_pct = 0
            aumento_pct = 0

        previo_px = int(previo_pct * MAX_BAR)
        aumento_px = int(aumento_pct * MAX_BAR)

        # Color del texto
        if aumento > 0:
            text_color = COLOR_INCREASE
        elif aumento < 0:
            text_color = COLOR_DECREASE
        else:
            text_color = COLOR_NO_CHANGE

        # Crear fila si no existe
        if path not in self.rows:
            frame = tk.Frame(self.container, bg=BG)
            frame.pack(anchor="nw", pady=5)

            text_widget = tk.Text(
                frame,
                font=("Consolas", 12),
                height=1,
                width=80,
                fg=text_color,
                bg=BG,
                relief="flat",
                highlightthickness=0
            )
            text_widget.insert("1.0", path)
            text_widget.configure(state="disabled")
            text_widget.pack(anchor="nw")

            canvas = tk.Canvas(
                frame,
                bg=BG,
                height=BAR_HEIGHT + 4,
                width=MAX_BAR + 10,
                highlightthickness=0
            )
            canvas.pack(anchor="nw")

            self.rows[path] = (text_widget, canvas)
        else:
            text_widget, canvas = self.rows[path]
            text_widget.configure(state="normal")
            text_widget.delete("1.0", "end")
            text_widget.insert("1.0", path)
            text_widget.configure(fg=text_color)
            text_widget.configure(state="disabled")
            canvas.delete("all")

        # Dibujar barra
        if previo_px > 0:
            canvas.create_rectangle(0, 2, previo_px, 2 + BAR_HEIGHT, fill="white", outline="")

        if aumento_px > 0:
            canvas.create_rectangle(previo_px, 2,
                                    previo_px + aumento_px, 2 + BAR_HEIGHT,
                                    fill="#ff6666", outline="")

        self.window.update()

# ============================
# 4. Monitor recursivo REAL
# ============================
def monitor_thread(gui, root_path, threshold_gb, interval_sec):
    print(f"[MONITOR] Escaneando TODA la partición: {root_path}")

    last_sizes = {}

    while True:
        for current_path, dirs, files in os.walk(root_path, topdown=True, onerror=lambda e: None):

            current_size = folder_size(current_path)

            if current_path not in last_sizes:
                last_sizes[current_path] = current_size
                continue

            previous = last_sizes[current_path]
            diff = current_size - previous
            diff_gb = diff / (1024**3)

            last_sizes[current_path] = current_size

            if abs(diff_gb) >= threshold_gb:
                gui.draw_row(current_path, previous, current_size)

        time.sleep(interval_sec)

# ============================
# 5. Inicio
# ============================
if __name__ == "__main__":

    ROOT = "C:\\"
    THRESHOLD_GB = 0.000001   # 1 KB
    INTERVAL_SEC = 5

    root = tk.Tk()
    root.withdraw()

    gui = MonitorGUI(root)

    t = threading.Thread(
        target=monitor_thread,
        args=(gui, ROOT, THRESHOLD_GB, INTERVAL_SEC),
        daemon=True
    )
    t.start()

    root.mainloop()
