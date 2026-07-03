# Mondisk

Monitor de disco para Windows que vigila una carpeta (o una partición completa) y avisa cuando el tamaño de alguna subcarpeta crece o se reduce por encima de un umbral configurable. Al detectar un cambio muestra un widget flotante con la ruta afectada y una barra estilo "antes/después", y opcionalmente reproduce un sonido de alarma. Vive como un ícono en la bandeja del sistema mientras corre en segundo plano.

## Cómo funciona

En cada ciclo, `main.py` recorre recursivamente la carpeta raíz configurada (`ruta_raiz`) y calcula el tamaño de cada subcarpeta en un único recorrido (bottom-up). Compara esos tamaños contra los del ciclo anterior; si alguna carpeta cambió más que `umbral_gb`, dispara:

- un widget sin bordes con la lista de rutas afectadas, cada una con una barra: tramo blanco = tamaño ya existente, tramo rojo = lo que creció, tramo naranja = lo que se liberó (disminución).
- una alarma sonora (si está activada).

El primer ciclo después de arrancar solo establece la línea base — no dispara alarmas — porque no hay un tamaño anterior con el cual comparar.

Como el tamaño de una carpeta incluye el de sus subcarpetas, un cambio en una carpeta profunda se propaga hacia arriba por toda la cadena de ancestros (si crece `C:\Users\Rodolfo\AppData\Local\Temp\PDF24`, también "crecen" `Temp`, `Local`, `AppData`, `Rodolfo` y `Users`). Para evitar reportar toda esa cadena, la carpeta raíz nunca se reporta a sí misma, y de cada cadena de carpetas cambiadas solo se muestra la más específica — sus ancestros quedan implícitos en ese aviso.

## Requisitos

- Windows (usa `winsound` y la bandeja del sistema de Windows).
- Python 3.10+.
- Dependencias en `requirements.txt`.

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

El ícono de la bandeja del sistema permite mostrar/ocultar el widget o salir de la app. Los botones ✕ y _ del widget minimizan/cierran según `minimizar_modo` (ver configuración).

## Configuración (`config.ini`)

| Sección | Clave | Descripción |
|---|---|---|
| `GENERAL` | `umbral_gb` | Cambio de tamaño (en GB) a partir del cual se dispara una alerta. |
| `GENERAL` | `ciclo_minutos` | Minutos de espera entre recorridos completos (mínimo real 0.1). No incluye el tiempo que tarda el propio recorrido. |
| `GENERAL` | `ruta_raiz` | Carpeta raíz a monitorear (ej. `C:\` para todo el disco, o una carpeta puntual para pruebas). |
| `COLORES` | `color_fondo` | Color de fondo del widget. |
| `COLORES` | `color_texto` | Color del texto de las rutas. |
| `COLORES` | `color_barra_base` | Color del tramo de tamaño ya existente en la barra. |
| `COLORES` | `color_barra_aumento` | Color del tramo de crecimiento en la barra. |
| `COLORES` | `color_barra_disminucion` | Color del tramo liberado cuando una carpeta se achica. |
| `FUENTE` | `familia` | Familia tipográfica del texto de las rutas. |
| `FUENTE` | `tamano` | Tamaño de fuente del texto de las rutas. |
| `VENTANA` | `minimizar_modo` | `detener` (cierra la app), `ocultar`/`barra_tareas` (oculta el widget; se restaura desde el ícono de bandeja). |
| `VENTANA` | `mostrar_consola` | `si`/`no`. Si es `no`, la ventana de consola del `.exe` se oculta por completo al arrancar (no solo su contenido) y solo queda el ícono de bandeja; se muestra una notificación "Se inició Mondisk" como confirmación. Al ejecutarse como script desde una terminal ya abierta, este ocultamiento no se aplica (evita ocultar la terminal del usuario). |
| `ALARMAS` | `sonido_activado` | `si`/`no`. |
| `ALARMAS` | `archivo_sonido` | Ruta al `.wav` de la alarma (relativa al `.exe`/script, o absoluta). |
| `ALARMAS` | `repetir` | Si repite el sonido varias veces al dispararse. |
| `ALARMAS` | `solo_importantes` | Reservado para futura distinción de severidad; actualmente la alarma ya solo suena al superar `umbral_gb`. |
| `EXCLUIDOS` | `carpetas` | Rutas a excluir del recorrido, separadas por `\|` (ej. `C:\Windows\|C:\Program Files`). |

Los valores booleanos aceptan `si`/`no`. Los comentarios inline se escriben con `;` (no usar `#`, que se reserva para los colores hexadecimales).

## Compilar a `.exe`

```powershell
.\.venv\Scripts\Activate.ps1
pip install pyinstaller
pyinstaller --onefile --name Mondisk --icon=icon.ico --add-data "icon.ico;." --add-data "alarma.wav;." main.py
```

Esto genera `dist\Mondisk.exe` con el ícono y el sonido de alarma embebidos. **`config.ini` no se empaqueta**: hay que copiarlo manualmente junto al `.exe` en `dist\`. Se deja afuera a propósito, para que sea editable y persista entre ejecuciones (un archivo empaquetado se extrae a una carpeta temporal descartable en cada corrida).

Por defecto la compilación conserva la consola (necesaria para que `mostrar_consola = si` tenga dónde imprimir). Para una app sin consola en absoluto, agregar `--windowed` al comando — en ese caso `mostrar_consola` deja de tener efecto.

## Limitaciones conocidas

- Monitorear `C:\` completo implica recorrer todo el disco en cada ciclo; en discos grandes esto puede tardar bastante más que `ciclo_minutos`, especialmente el primer recorrido (que además nunca dispara alertas).
- La ventana del widget no tiene decoraciones (`overrideredirect`), por lo que Windows no le asigna ícono propio en la barra de tareas — la presencia en la barra la da el ícono de bandeja del sistema, no el widget en sí.
