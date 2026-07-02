import os
import time
import threading
import tkinter as tk
import configparser
import sys
import platform

import simpleaudio as sa
import pystray
from PIL import Image

try:
    from playsound import playsound
except ImportError:
    playsound = None

if platform.system() == "Windows":
    import winsound

# ============================
# RUTAS (fuente vs. .exe empaquetado con PyInstaller)
# ============================
def resource_path(relative_path):
    """Ruta a un recurso empaquetado dentro del .exe (icon.ico, alarma.wav)."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def external_path(relative_path):
    """Ruta a un archivo editable junto al .exe (o al script), ej. config.ini."""
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ============================
# LEER CONFIGURACIÓN
# ============================
config = configparser.ConfigParser(inline_comment_prefixes=(";",))
config.read(external_path("config.ini"))

UMBRAL_GB = float(config["GENERAL"]["umbral_gb"])
CICLO_MINUTOS = max(float(config["GENERAL"]["ciclo_minutos"]), 0.1)
RUTA_RAIZ = config["GENERAL"].get("ruta_raiz", "C:\\").strip()

COLOR_FONDO = config["COLORES"]["color_fondo"]
COLOR_TEXTO = config["COLORES"]["color_texto"]
COLOR_BARRA_BASE = config["COLORES"]["color_barra_base"]
COLOR_BARRA_AUMENTO = config["COLORES"]["color_barra_aumento"]
COLOR_BARRA_DISMINUCION = config["COLORES"]["color_barra_disminucion"]

FUENTE_FAMILIA = config["FUENTE"].get("familia", "Consolas").strip()
FUENTE_TAMANO = int(config["FUENTE"].get("tamano", "12"))

MINIMIZAR_MODO = config["VENTANA"]["minimizar_modo"]
MOSTRAR_CONSOLA = config["VENTANA"]["mostrar_consola"].split()[0].lower() == "si"

SONIDO_ACTIVADO = config["ALARMAS"]["sonido_activado"].split()[0].lower() == "si"
ARCHIVO_SONIDO = config["ALARMAS"]["archivo_sonido"]
if ARCHIVO_SONIDO and not os.path.isabs(ARCHIVO_SONIDO):
    ARCHIVO_SONIDO = resource_path(ARCHIVO_SONIDO)
REPETIR_SONIDO = config["ALARMAS"]["repetir"].split()[0].lower() == "si"
SOLO_IMPORTANTES = config["ALARMAS"]["solo_importantes"].split()[0].lower() == "si"

EXCLUIR_CARPETAS = []
if config.has_section("EXCLUIDOS") and "carpetas" in config["EXCLUIDOS"]:
    EXCLUIR_CARPETAS = [p.strip().replace("\\\\", "\\") for p in config["EXCLUIDOS"]["carpetas"].split("|") if p.strip()]

if not MOSTRAR_CONSOLA:
    sys.stdout = open(os.devnull, "w")

# ============================
# CONFIGURACIÓN FIJA
# ============================
GB = 1024 * 1024 * 1024
MAX_GB = 10
BAR_HEIGHT = 18
MAX_BAR = 300

# ============================
# 1. Tamaño de carpetas (recorrido único, bottom-up)
# ============================
def is_excluded(path):
    return any(path.startswith(ex) for ex in EXCLUIR_CARPETAS)


def compute_all_sizes(root_path):
    """Calcula el tamaño de cada carpeta del árbol en un solo recorrido.

    Se recolectan las entradas en pre-orden (padre antes que hijos) y luego
    se procesan en orden inverso, de modo que al llegar a una carpeta ya se
    conoce el tamaño acumulado de sus subcarpetas inmediatas.
    """
    entries = []
    for current_path, dirs, files in os.walk(root_path, topdown=True, onerror=lambda e: None):
        dirs[:] = [d for d in dirs if not is_excluded(os.path.join(current_path, d))]
        entries.append((current_path, list(dirs), files))

    sizes = {}
    for current_path, dirs, files in reversed(entries):
        total = 0
        for f in files:
            try:
                total += os.path.getsize(os.path.join(current_path, f))
            except OSError:
                pass
        for d in dirs:
            total += sizes.get(os.path.join(current_path, d), 0)
        sizes[current_path] = total
    return sizes

# ============================
# 2. Reproducción de sonido
# ============================
def play_alarm_once():
    if not SONIDO_ACTIVADO:
        return
    if not ARCHIVO_SONIDO or not os.path.exists(ARCHIVO_SONIDO):
        return

    def _play():
        try:
            # Windows + WAV → winsound
            if platform.system() == "Windows" and ARCHIVO_SONIDO.lower().endswith(".wav"):
                winsound.PlaySound(
                    ARCHIVO_SONIDO,
                    winsound.SND_FILENAME | winsound.SND_ASYNC
                )
            # WAV genérico → simpleaudio
            elif ARCHIVO_SONIDO.lower().endswith(".wav"):
                wave_obj = sa.WaveObject.from_wave_file(ARCHIVO_SONIDO)
                play_obj = wave_obj.play()
                # Wait briefly to ensure sound starts
                time.sleep(0.1)
            # Otros formatos → playsound si está instalado
            elif playsound is not None:
                playsound(ARCHIVO_SONIDO, block=False)
        except Exception as e:
            print(f"Error playing sound: {e}", file=sys.stderr)

    threading.Thread(target=_play, daemon=True).start()

def play_alarm():
    if not REPETIR_SONIDO:
        play_alarm_once()
        return

    def _loop():
        for _ in range(3):  # repetir 3 veces
            play_alarm_once()
            time.sleep(1.5)

    threading.Thread(target=_loop, daemon=True).start()

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

        self.window = tk.Toplevel(self.root)
        try:
            self.window.iconphoto(False, tk.PhotoImage(file=resource_path("icon.ico")))
        except:
            pass
        self.window.overrideredirect(True)
        self.window.configure(bg=COLOR_FONDO)
        self.window.geometry("420x300")

        self.bg = tk.Canvas(self.window, bg=COLOR_FONDO, highlightthickness=0)
        self.bg.pack(fill="both", expand=True)

        w, h, r = 420, 300, 20

        self.bg.create_arc((0, 0, r*2, r*2), start=90, extent=90, fill=COLOR_FONDO, outline=COLOR_FONDO)
        self.bg.create_arc((w-r*2, 0, w, r*2), start=0, extent=90, fill=COLOR_FONDO, outline=COLOR_FONDO)
        self.bg.create_arc((0, h-r*2, r*2, h), start=180, extent=90, fill=COLOR_FONDO, outline=COLOR_FONDO)
        self.bg.create_arc((w-r*2, h-r*2, w, h), start=270, extent=90, fill=COLOR_FONDO, outline=COLOR_FONDO)
        self.bg.create_rectangle(r, 0, w-r, h, fill=COLOR_FONDO, outline=COLOR_FONDO)
        self.bg.create_rectangle(0, r, w, h-r, fill=COLOR_FONDO, outline=COLOR_FONDO)

        # Botón cerrar ✕
        self.close_btn = tk.Button(
            self.window,
            text="✕",
            fg="white",
            bg="#444444",
            font=("Consolas", 12),
            padx=5,
            pady=2,
            relief="flat",
            highlightthickness=0,
            activebackground="#555555",
            activeforeground="white"
        )
        self.close_btn.place(x=w-30, y=10)
        self.close_btn.place_forget()

        def close_app(event=None):
            if MINIMIZAR_MODO == "detener":
                os._exit(0)
            else:
                self.window.withdraw()

        self.close_btn.bind("<Button-1>", close_app)

        # Botón minimizar _
        self.min_btn = tk.Button(
            self.window,
            text="_",
            fg="white",
            bg="#444444",
            font=("Consolas", 12),
            padx=5,
            pady=2,
            relief="flat",
            highlightthickness=0,
            activebackground="#555555",
            activeforeground="white"
        )
        self.min_btn.place(x=w-60, y=10)
        self.min_btn.place_forget()

        def minimize_app(event=None):
            self.window.withdraw()

        self.min_btn.bind("<Button-1>", minimize_app)

        # Mostrar/ocultar botones
        def show_buttons(event):
            self.close_btn.place(x=w-30, y=10)
            self.min_btn.place(x=w-60, y=10)

        def hide_buttons(event):
            self.close_btn.place_forget()
            self.min_btn.place_forget()

        self.window.bind("<Enter>", show_buttons)
        self.window.bind("<Leave>", hide_buttons)

        # Mover ventana con botón derecho
        def start_move(event):
            self._drag_x = event.x
            self._drag_y = event.y

        def do_move(event):
            x = self.window.winfo_x() + (event.x - self._drag_x)
            y = self.window.winfo_y() + (event.y - self._drag_y)
            self.window.geometry(f"+{x}+{y}")

        self.window.bind("<Button-3>", start_move)
        self.window.bind("<B3-Motion>", do_move)

        # Área scrollable
        self.content_canvas = tk.Canvas(self.window, bg=COLOR_FONDO, highlightthickness=0)
        self.content_canvas.place(x=10, y=40, width=380, height=240)

        self.scrollbar = tk.Scrollbar(self.window, orient="vertical", command=self.content_canvas.yview)
        self.scrollbar.place(x=390, y=40, height=240)

        self.content_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.container = tk.Frame(self.content_canvas, bg=COLOR_FONDO)
        self.content_canvas.create_window((0, 0), window=self.container, anchor="nw")

        def on_configure(event):
            self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))

        self.container.bind("<Configure>", on_configure)

    def draw_row(self, path, previo, actual):
        self.create_window()

        aumento = actual - previo

        previo_pct = previo / (MAX_GB * GB)
        nuevo_pct = actual / (MAX_GB * GB)

        extent_pct = max(previo_pct, nuevo_pct)
        if extent_pct > 1:
            factor = 1 / extent_pct
            previo_pct *= factor
            nuevo_pct *= factor

        previo_px = int(previo_pct * MAX_BAR)
        nuevo_px = int(nuevo_pct * MAX_BAR)

        if path not in self.rows:
            frame = tk.Frame(self.container, bg=COLOR_FONDO)
            frame.pack(anchor="nw", pady=5)

            text_widget = tk.Text(
                frame,
                font=(FUENTE_FAMILIA, FUENTE_TAMANO),
                height=1,
                width=80,
                fg=COLOR_TEXTO,
                bg=COLOR_FONDO,
                relief="flat",
                highlightthickness=0
            )
            text_widget.insert("1.0", path)
            text_widget.configure(state="disabled")
            text_widget.pack(anchor="nw")

            canvas = tk.Canvas(
                frame,
                bg=COLOR_FONDO,
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
            text_widget.configure(state="disabled")
            canvas.delete("all")

        if aumento >= 0:
            if previo_px > 0:
                canvas.create_rectangle(0, 2, previo_px, 2 + BAR_HEIGHT, fill=COLOR_BARRA_BASE, outline="")
            if nuevo_px > previo_px:
                canvas.create_rectangle(previo_px, 2, nuevo_px, 2 + BAR_HEIGHT, fill=COLOR_BARRA_AUMENTO, outline="")
        else:
            if nuevo_px > 0:
                canvas.create_rectangle(0, 2, nuevo_px, 2 + BAR_HEIGHT, fill=COLOR_BARRA_BASE, outline="")
            if previo_px > nuevo_px:
                canvas.create_rectangle(nuevo_px, 2, previo_px, 2 + BAR_HEIGHT, fill=COLOR_BARRA_DISMINUCION, outline="")

        self.window.update()

# ============================
# 4. Icono de bandeja del sistema
# ============================
def setup_tray_icon(gui):
    try:
        image = Image.open(resource_path("icon.ico"))
    except Exception:
        image = Image.new("RGB", (64, 64), color="#9f9df2")

    def toggle_window(icon, item):
        def _toggle():
            if gui.window is None:
                return
            if gui.window.state() == "withdrawn":
                gui.window.deiconify()
            else:
                gui.window.withdraw()
        gui.root.after(0, _toggle)

    def quit_app(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Mostrar/Ocultar", toggle_window, default=True),
        pystray.MenuItem("Salir", quit_app),
    )

    tray_icon = pystray.Icon("mondisk", image, "Mondisk Monitor", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()
    return tray_icon

# ============================
# 5. Monitor recursivo REAL
# ============================
def monitor_thread(gui, root_path, threshold_gb, ciclo_minutos):
    last_sizes = {}
    intervalo = ciclo_minutos * 60
    first_pass = True

    while True:
        sizes = compute_all_sizes(root_path)

        if not first_pass:
            for current_path, current_size in sizes.items():
                previous = last_sizes.get(current_path)
                if previous is None:
                    continue

                diff_gb = (current_size - previous) / GB

                if abs(diff_gb) >= threshold_gb:
                    gui.root.after(0, gui.draw_row, current_path, previous, current_size)

                    if SONIDO_ACTIVADO and (not SOLO_IMPORTANTES or abs(diff_gb) >= threshold_gb):
                        play_alarm()

        last_sizes = sizes
        first_pass = False
        time.sleep(intervalo)

# ============================
# 6. Inicio
# ============================
if __name__ == "__main__":

    ROOT = RUTA_RAIZ

    print("=== Mondisk Monitor Started ===")
    print(f"Monitoring root: {ROOT}")
    print(f"Threshold: {UMBRAL_GB} GB")
    print(f"Cycle: {CICLO_MINUTOS} minutes ({CICLO_MINUTOS * 60} seconds)")
    print(f"Show console: {MOSTRAR_CONSOLA}")

    root = tk.Tk()
    try:
        root.iconphoto(False, tk.PhotoImage(file=resource_path("icon.ico")))
    except:
        pass
    root.withdraw()

    gui = MonitorGUI(root)
    tray_icon = setup_tray_icon(gui)

    t = threading.Thread(
        target=monitor_thread,
        args=(gui, ROOT, UMBRAL_GB, CICLO_MINUTOS),
        daemon=True
    )
    t.start()

    root.mainloop()
