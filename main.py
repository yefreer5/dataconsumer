"""
Data Consumer - Consume datos moviles sin descargar archivos al dispositivo.
Lee datos en memoria y los descarta. Tambien sube datos para consumir en ambas direcciones.
Muestra velocidad, consumo acumulado y permite definir un objetivo en MB o GB.
"""

import os
import threading
import time
import urllib.request
import urllib.error
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp

# --- URLs de prueba de velocidad (solo lectura en memoria, nada se guarda) ---
DOWNLOAD_URLS = [
    "http://speedtest.tele2.net/100MB.zip",
    "http://speedtest.tele2.net/10MB.zip",
    "http://proof.ovh.net/files/100Mb.dat",
    "http://proof.ovh.net/files/10Mb.dat",
    "http://ipv4.download.thinkbroadband.com/100MB.zip",
    "http://ipv4.download.thinkbroadband.com/10MB.zip",
]

# URLs para subir datos (upload) - consumen datos de subida
UPLOAD_URLS = [
    "http://speedtest.tele2.net/upload.php",
    "http://speed.hetzner.de/upload.php",
]

CHUNK_SIZE = 131072  # 128 KB por lectura (mas rapido)
UPLOAD_BLOCK_SIZE = 1_048_576  # 1 MB por bloque de subida


class DataConsumerApp(App):
    def build(self):
        self.title = "Data Consumer"
        self.total_bytes = 0
        self.target_bytes = 0
        self.running = False
        self.speed_bytes = 0
        self.speed_tracker_bytes = 0
        self.lock = threading.Lock()

        Window.clearcolor = (0.08, 0.08, 0.11, 1)

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))

        # Titulo
        root.add_widget(Label(
            text="[b]DATA CONSUMER[/b]",
            markup=True, font_size=dp(24),
            size_hint_y=None, height=dp(40),
            color=(0.3, 0.75, 1, 1),
        ))

        root.add_widget(Label(
            text="Consume datos sin guardar archivos",
            font_size=dp(12),
            size_hint_y=None, height=dp(20),
            color=(0.5, 0.5, 0.5, 1),
        ))

        # Velocidad
        self.speed_label = Label(
            text="0.00 Mbps",
            font_size=dp(34), bold=True,
            size_hint_y=None, height=dp(50),
            color=(0.2, 0.95, 0.4, 1),
        )
        root.add_widget(self.speed_label)

        # Consumido
        self.consumed_label = Label(
            text="Consumido: 0.00 MB",
            font_size=dp(20),
            size_hint_y=None, height=dp(38),
            color=(1, 1, 1, 1),
        )
        root.add_widget(self.consumed_label)

        # Objetivo display
        self.target_display = Label(
            text="Objetivo: --",
            font_size=dp(14),
            size_hint_y=None, height=dp(25),
            color=(0.6, 0.6, 0.6, 1),
        )
        root.add_widget(self.target_display)

        # Progreso
        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(22))
        root.add_widget(self.progress)

        self.progress_label = Label(
            text="0.0%", font_size=dp(13),
            size_hint_y=None, height=dp(22),
            color=(0.75, 0.75, 0.75, 1),
        )
        root.add_widget(self.progress_label)

        # --- Cantidad objetivo ---
        row1 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(46), spacing=dp(8))
        row1.add_widget(Label(text="Cantidad:", font_size=dp(15), size_hint_x=0.28, color=(0.8, 0.8, 0.8, 1)))
        self.target_input = TextInput(
            text="100", input_filter="float", font_size=dp(17),
            multiline=False, size_hint_x=0.35,
            background_color=(0.16, 0.16, 0.2, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.3, 0.75, 1, 1),
            padding=[dp(10), dp(8), 0, 0],
        )
        row1.add_widget(self.target_input)
        self.unit_spinner = Spinner(
            text="MB", values=("MB", "GB"),
            font_size=dp(15), size_hint_x=0.37,
            background_color=(0.2, 0.2, 0.26, 1), color=(1, 1, 1, 1),
        )
        row1.add_widget(self.unit_spinner)
        root.add_widget(row1)

        # --- Modo ---
        row_mode = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(46), spacing=dp(8))
        row_mode.add_widget(Label(text="Modo:", font_size=dp(15), size_hint_x=0.28, color=(0.8, 0.8, 0.8, 1)))
        self.mode_spinner = Spinner(
            text="Descarga + Subida", values=("Descarga + Subida", "Solo Descarga", "Solo Subida"),
            font_size=dp(14), size_hint_x=0.72,
            background_color=(0.2, 0.2, 0.26, 1), color=(1, 1, 1, 1),
        )
        row_mode.add_widget(self.mode_spinner)
        root.add_widget(row_mode)

        # --- Hilos ---
        row2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(46), spacing=dp(8))
        row2.add_widget(Label(text="Hilos:", font_size=dp(15), size_hint_x=0.28, color=(0.8, 0.8, 0.8, 1)))
        self.threads_spinner = Spinner(
            text="4", values=("1", "2", "3", "4", "6", "8", "10", "12"),
            font_size=dp(15), size_hint_x=0.72,
            background_color=(0.2, 0.2, 0.26, 1), color=(1, 1, 1, 1),
        )
        row2.add_widget(self.threads_spinner)
        root.add_widget(row2)

        # --- Botones ---
        btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(10))
        self.start_btn = Button(
            text="INICIAR", font_size=dp(17),
            background_color=(0.1, 0.65, 0.25, 1), background_normal="",
            color=(1, 1, 1, 1),
        )
        self.start_btn.bind(on_press=self.start_consuming)
        btn_row.add_widget(self.start_btn)

        self.stop_btn = Button(
            text="DETENER", font_size=dp(17),
            background_color=(0.7, 0.15, 0.15, 1), background_normal="",
            color=(1, 1, 1, 1), disabled=True,
        )
        self.stop_btn.bind(on_press=self.stop_consuming)
        btn_row.add_widget(self.stop_btn)
        root.add_widget(btn_row)

        # Reset
        self.reset_btn = Button(
            text="REINICIAR CONTADOR", font_size=dp(13),
            size_hint_y=None, height=dp(40),
            background_color=(0.3, 0.3, 0.35, 1), background_normal="",
            color=(1, 1, 1, 1),
        )
        self.reset_btn.bind(on_press=self.reset_counter)
        root.add_widget(self.reset_btn)

        # Estado
        self.status_label = Label(
            text="Listo", font_size=dp(12),
            size_hint_y=None, height=dp(25),
            color=(0.45, 0.45, 0.45, 1),
        )
        root.add_widget(self.status_label)

        root.add_widget(Label(size_hint_y=1))

        Clock.schedule_interval(self.update_ui, 0.5)
        return root

    # --- Utilidades ---

    def fmt(self, nbytes):
        if nbytes >= 1_073_741_824:
            return f"{nbytes / 1_073_741_824:.2f} GB"
        if nbytes >= 1_048_576:
            return f"{nbytes / 1_048_576:.2f} MB"
        if nbytes >= 1024:
            return f"{nbytes / 1024:.2f} KB"
        return f"{nbytes} B"

    def _add_bytes(self, n):
        with self.lock:
            self.total_bytes += n
            self.speed_tracker_bytes += n

    def _reached_target(self):
        return self.target_bytes > 0 and self.total_bytes >= self.target_bytes

    # --- Controles ---

    def start_consuming(self, *_):
        try:
            amount = float(self.target_input.text)
        except ValueError:
            self.status_label.text = "Escribe un numero valido"
            return
        if amount <= 0:
            self.status_label.text = "Debe ser mayor a 0"
            return

        mult = 1_073_741_824 if self.unit_spinner.text == "GB" else 1_048_576
        self.target_bytes = int(amount * mult)
        self.target_display.text = f"Objetivo: {amount} {self.unit_spinner.text}"
        self.running = True

        for w in (self.start_btn, self.target_input, self.unit_spinner, self.threads_spinner, self.mode_spinner):
            w.disabled = True
        self.stop_btn.disabled = False
        self.status_label.text = "Consumiendo datos..."
        self.status_label.color = (0.3, 0.75, 1, 1)

        n_threads = int(self.threads_spinner.text)
        mode = self.mode_spinner.text

        if mode in ("Descarga + Subida", "Solo Descarga"):
            dl_threads = n_threads if mode == "Solo Descarga" else max(1, n_threads // 2)
            for i in range(dl_threads):
                threading.Thread(target=self._download_worker, args=(i,), daemon=True).start()

        if mode in ("Descarga + Subida", "Solo Subida"):
            ul_threads = n_threads if mode == "Solo Subida" else max(1, n_threads - n_threads // 2)
            for i in range(ul_threads):
                threading.Thread(target=self._upload_worker, args=(i,), daemon=True).start()

        threading.Thread(target=self._speed_loop, daemon=True).start()

    def stop_consuming(self, *_):
        self.running = False
        for w in (self.start_btn, self.target_input, self.unit_spinner, self.threads_spinner, self.mode_spinner):
            w.disabled = False
        self.stop_btn.disabled = True
        self.status_label.text = "Detenido"
        self.status_label.color = (0.9, 0.6, 0.1, 1)

    def reset_counter(self, *_):
        if not self.running:
            with self.lock:
                self.total_bytes = 0
            self.progress.value = 0
            self.progress_label.text = "0.0%"
            self.consumed_label.text = "Consumido: 0.00 MB"
            self.status_label.text = "Reiniciado"

    # --- Workers ---

    def _download_worker(self, tid):
        """Lee datos en memoria y los descarta inmediatamente. No guarda nada."""
        idx = tid % len(DOWNLOAD_URLS)
        while self.running and not self._reached_target():
            url = DOWNLOAD_URLS[idx]
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "Mozilla/5.0 (Linux; Android 12)")
                resp = urllib.request.urlopen(req, timeout=20)
                while self.running and not self._reached_target():
                    chunk = resp.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    self._add_bytes(len(chunk))
                    del chunk  # descarta datos inmediatamente
                resp.close()
            except Exception:
                time.sleep(2)
            idx = (idx + 1) % len(DOWNLOAD_URLS)
        self._check_done()

    def _upload_worker(self, tid):
        """Sube bloques de datos aleatorios a servidores de prueba. Consume datos de subida."""
        idx = tid % len(UPLOAD_URLS)
        # Generar bloque reutilizable de datos aleatorios
        random_block = os.urandom(UPLOAD_BLOCK_SIZE)

        while self.running and not self._reached_target():
            url = UPLOAD_URLS[idx]
            try:
                req = urllib.request.Request(
                    url,
                    data=random_block,
                    method="POST",
                )
                req.add_header("User-Agent", "Mozilla/5.0 (Linux; Android 12)")
                req.add_header("Content-Type", "application/octet-stream")
                resp = urllib.request.urlopen(req, timeout=20)
                resp.read()
                resp.close()
                self._add_bytes(UPLOAD_BLOCK_SIZE)
            except Exception:
                time.sleep(2)
            idx = (idx + 1) % len(UPLOAD_URLS)
        self._check_done()

    def _speed_loop(self):
        while self.running:
            with self.lock:
                self.speed_bytes = self.speed_tracker_bytes
                self.speed_tracker_bytes = 0
            time.sleep(1)
        with self.lock:
            self.speed_bytes = 0

    def _check_done(self):
        if self._reached_target() and self.running:
            Clock.schedule_once(lambda dt: self._on_target_reached())

    def _on_target_reached(self):
        if not self.running:
            return
        self.stop_consuming()
        self.status_label.text = "Objetivo alcanzado!"
        self.status_label.color = (0.2, 0.95, 0.4, 1)

    # --- UI ---

    def update_ui(self, _dt):
        with self.lock:
            total = self.total_bytes
            speed = self.speed_bytes

        self.consumed_label.text = f"Consumido: {self.fmt(total)}"
        self.speed_label.text = f"{(speed * 8) / 1_000_000:.2f} Mbps"

        if self.target_bytes > 0:
            pct = min(100.0, (total / self.target_bytes) * 100)
            self.progress.value = pct
            self.progress_label.text = f"{pct:.1f}%"


if __name__ == "__main__":
    DataConsumerApp().run()
