"""
Data Consumer - Consume datos moviles sin descargar archivos.
Descarga y sube datos en memoria para consumir datos moviles.
"""

import os
import threading
import time
import urllib.request

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

# URLs de speedtest publicos (HTTPS obligatorio en Android 9+)
DOWNLOAD_URLS = [
    "https://speed.hetzner.de/100MB.bin",
    "https://speed.hetzner.de/10MB.bin",
    "https://ash-speed.hetzner.com/100MB.bin",
    "https://ash-speed.hetzner.com/10MB.bin",
]

UPLOAD_URL = "https://speed.hetzner.de/upload.php"

CHUNK = 65536
UPLOAD_BLOCK = 524288


class DataConsumerApp(App):

    def build(self):
        self.title = "Data Consumer"
        self.total = 0
        self.target = 0
        self.running = False
        self.speed = 0
        self._speed_acc = 0
        self._lock = threading.Lock()

        Window.clearcolor = (0.08, 0.08, 0.11, 1)

        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(6))

        root.add_widget(Label(
            text="DATA CONSUMER", font_size=dp(22), bold=True,
            size_hint_y=None, height=dp(36), color=(0.3, 0.75, 1, 1)))

        root.add_widget(Label(
            text="Consume datos moviles", font_size=dp(12),
            size_hint_y=None, height=dp(18), color=(0.5, 0.5, 0.5, 1)))

        self.lbl_speed = Label(
            text="0.00 Mbps", font_size=dp(30), bold=True,
            size_hint_y=None, height=dp(44), color=(0.2, 0.95, 0.4, 1))
        root.add_widget(self.lbl_speed)

        self.lbl_used = Label(
            text="Consumido: 0.00 MB", font_size=dp(18),
            size_hint_y=None, height=dp(32), color=(1, 1, 1, 1))
        root.add_widget(self.lbl_used)

        self.lbl_target = Label(
            text="Objetivo: --", font_size=dp(13),
            size_hint_y=None, height=dp(22), color=(0.6, 0.6, 0.6, 1))
        root.add_widget(self.lbl_target)

        self.bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(20))
        root.add_widget(self.bar)

        self.lbl_pct = Label(
            text="0 %", font_size=dp(12),
            size_hint_y=None, height=dp(20), color=(0.7, 0.7, 0.7, 1))
        root.add_widget(self.lbl_pct)

        # Cantidad
        r1 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        r1.add_widget(Label(text="Cantidad:", font_size=dp(14),
                            size_hint_x=0.3, color=(0.8, 0.8, 0.8, 1)))
        self.inp = TextInput(
            text="100", input_filter="float", font_size=dp(16),
            multiline=False, size_hint_x=0.35,
            background_color=(0.15, 0.15, 0.2, 1),
            foreground_color=(1, 1, 1, 1))
        r1.add_widget(self.inp)
        self.unit = Spinner(
            text="MB", values=("MB", "GB"),
            font_size=dp(14), size_hint_x=0.35,
            background_color=(0.2, 0.2, 0.26, 1), color=(1, 1, 1, 1))
        r1.add_widget(self.unit)
        root.add_widget(r1)

        # Modo
        r2 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        r2.add_widget(Label(text="Modo:", font_size=dp(14),
                            size_hint_x=0.3, color=(0.8, 0.8, 0.8, 1)))
        self.mode = Spinner(
            text="Descarga", values=("Descarga", "Subida", "Ambos"),
            font_size=dp(13), size_hint_x=0.7,
            background_color=(0.2, 0.2, 0.26, 1), color=(1, 1, 1, 1))
        r2.add_widget(self.mode)
        root.add_widget(r2)

        # Hilos
        r3 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        r3.add_widget(Label(text="Hilos:", font_size=dp(14),
                            size_hint_x=0.3, color=(0.8, 0.8, 0.8, 1)))
        self.threads = Spinner(
            text="4", values=("1", "2", "3", "4", "6", "8"),
            font_size=dp(14), size_hint_x=0.7,
            background_color=(0.2, 0.2, 0.26, 1), color=(1, 1, 1, 1))
        r3.add_widget(self.threads)
        root.add_widget(r3)

        # Botones
        btns = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.btn_start = Button(
            text="INICIAR", font_size=dp(16),
            background_color=(0.1, 0.65, 0.25, 1), background_normal="",
            color=(1, 1, 1, 1))
        self.btn_start.bind(on_press=self.do_start)
        btns.add_widget(self.btn_start)

        self.btn_stop = Button(
            text="DETENER", font_size=dp(16),
            background_color=(0.7, 0.15, 0.15, 1), background_normal="",
            color=(1, 1, 1, 1), disabled=True)
        self.btn_stop.bind(on_press=self.do_stop)
        btns.add_widget(self.btn_stop)
        root.add_widget(btns)

        self.btn_reset = Button(
            text="REINICIAR", font_size=dp(13),
            size_hint_y=None, height=dp(38),
            background_color=(0.3, 0.3, 0.35, 1), background_normal="",
            color=(1, 1, 1, 1))
        self.btn_reset.bind(on_press=self.do_reset)
        root.add_widget(self.btn_reset)

        self.lbl_status = Label(
            text="Listo", font_size=dp(11),
            size_hint_y=None, height=dp(22), color=(0.45, 0.45, 0.45, 1))
        root.add_widget(self.lbl_status)

        root.add_widget(Label(size_hint_y=1))

        Clock.schedule_interval(self._tick, 0.5)
        return root

    # -- helpers --

    @staticmethod
    def _fmt(n):
        if n >= 1073741824:
            return "{:.2f} GB".format(n / 1073741824.0)
        if n >= 1048576:
            return "{:.2f} MB".format(n / 1048576.0)
        if n >= 1024:
            return "{:.2f} KB".format(n / 1024.0)
        return "{} B".format(n)

    def _add(self, n):
        with self._lock:
            self.total += n
            self._speed_acc += n

    def _done(self):
        return self.target > 0 and self.total >= self.target

    # -- controls --

    def do_start(self, *_a):
        try:
            amt = float(self.inp.text)
        except Exception:
            self.lbl_status.text = "Numero invalido"
            return
        if amt <= 0:
            self.lbl_status.text = "Debe ser > 0"
            return

        mult = 1073741824 if self.unit.text == "GB" else 1048576
        self.target = int(amt * mult)
        self.lbl_target.text = "Objetivo: {} {}".format(amt, self.unit.text)
        self.running = True

        self.btn_start.disabled = True
        self.inp.disabled = True
        self.unit.disabled = True
        self.mode.disabled = True
        self.threads.disabled = True
        self.btn_stop.disabled = False
        self.lbl_status.text = "Consumiendo..."
        self.lbl_status.color = (0.3, 0.75, 1, 1)

        nt = int(self.threads.text)
        m = self.mode.text

        if m in ("Descarga", "Ambos"):
            nd = nt if m == "Descarga" else max(1, nt // 2)
            for i in range(nd):
                t = threading.Thread(target=self._dl, args=(i,))
                t.daemon = True
                t.start()

        if m in ("Subida", "Ambos"):
            nu = nt if m == "Subida" else max(1, nt - nt // 2)
            for i in range(nu):
                t = threading.Thread(target=self._ul, args=(i,))
                t.daemon = True
                t.start()

        t = threading.Thread(target=self._spd)
        t.daemon = True
        t.start()

    def do_stop(self, *_a):
        self.running = False
        self.btn_start.disabled = False
        self.inp.disabled = False
        self.unit.disabled = False
        self.mode.disabled = False
        self.threads.disabled = False
        self.btn_stop.disabled = True
        self.lbl_status.text = "Detenido"
        self.lbl_status.color = (0.9, 0.6, 0.1, 1)

    def do_reset(self, *_a):
        if not self.running:
            with self._lock:
                self.total = 0
            self.bar.value = 0
            self.lbl_pct.text = "0 %"
            self.lbl_used.text = "Consumido: 0.00 MB"
            self.lbl_status.text = "Reiniciado"

    # -- workers --

    def _dl(self, tid):
        idx = tid % len(DOWNLOAD_URLS)
        while self.running and not self._done():
            url = DOWNLOAD_URLS[idx]
            try:
                req = urllib.request.Request(url)
                req.add_header("User-Agent", "DataConsumer/2.0")
                resp = urllib.request.urlopen(req, timeout=15)
                while self.running and not self._done():
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    self._add(len(chunk))
                resp.close()
            except Exception:
                pass
            time.sleep(0.5)
            idx = (idx + 1) % len(DOWNLOAD_URLS)
        self._maybe_finish()

    def _ul(self, tid):
        block = os.urandom(UPLOAD_BLOCK)
        while self.running and not self._done():
            try:
                req = urllib.request.Request(UPLOAD_URL, data=block, method="POST")
                req.add_header("User-Agent", "DataConsumer/2.0")
                req.add_header("Content-Type", "application/octet-stream")
                resp = urllib.request.urlopen(req, timeout=15)
                resp.read()
                resp.close()
                self._add(UPLOAD_BLOCK)
            except Exception:
                pass
            time.sleep(0.5)
        self._maybe_finish()

    def _spd(self):
        while self.running:
            with self._lock:
                self.speed = self._speed_acc
                self._speed_acc = 0
            time.sleep(1)
        with self._lock:
            self.speed = 0

    def _maybe_finish(self):
        if self._done() and self.running:
            Clock.schedule_once(lambda dt: self._on_finish())

    def _on_finish(self):
        if not self.running:
            return
        self.do_stop()
        self.lbl_status.text = "Objetivo alcanzado!"
        self.lbl_status.color = (0.2, 0.95, 0.4, 1)

    # -- ui update --

    def _tick(self, _dt):
        with self._lock:
            t = self.total
            s = self.speed

        self.lbl_used.text = "Consumido: {}".format(self._fmt(t))
        self.lbl_speed.text = "{:.2f} Mbps".format((s * 8) / 1000000.0)

        if self.target > 0:
            p = min(100.0, (t / float(self.target)) * 100)
            self.bar.value = p
            self.lbl_pct.text = "{:.1f} %".format(p)


if __name__ == "__main__":
    DataConsumerApp().run()
