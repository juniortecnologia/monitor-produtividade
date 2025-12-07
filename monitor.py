import os
import time
import threading
import json
import tkinter as as_tk
from tkinter import filedialog, messagebox
import pyautogui
from datetime import datetime
import sys
import winreg
from PIL import Image, ImageDraw
import pystray

# --- Configurações Globais ---
CONFIG_FILE = "config.json"
APP_NAME = "MonitorScreenshots"
INTERVALO_SEGUNDOS = 300  # 5 Minutos

class MonitorApp:
    def __init__(self):
        self.running = True
        self.config = self.load_config()
        self.icon = None
        self.thread = threading.Thread(target=self.loop_screenshots)
        self.thread.daemon = True
        
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"destination_path": "", "auto_start": False}

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    def set_autostart(self, enable):
        """Adiciona ou remove o programa do registro do Windows para iniciar com o sistema."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            exe_path = os.path.abspath(sys.argv[0])
            
            # Se estiver rodando como script .py, apontar para o executável do python
            if not exe_path.endswith(".exe"):
                 exe_path = f'"{sys.executable}" "{exe_path}"'
            else:
                 exe_path = f'"{exe_path}"'

            if enable:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Erro no registro: {e}")

    def create_image(self):
        """Gera um ícone simples (quadrado azul) para a bandeja."""
        width = 64
        height = 64
        color1 = (0, 120, 215)
        color2 = (255, 255, 255)
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=color2)
        return image

    def take_screenshot(self):
        path = self.config.get("destination_path")
        if not path or not os.path.exists(path):
            return # Caminho inválido ou NAS offline

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"screen_{timestamp}.png"
            fullpath = os.path.join(path, filename)
            
            screenshot = pyautogui.screenshot()
            screenshot.save(fullpath)
        except Exception as e:
            print(f"Erro ao salvar: {e}")

    def loop_screenshots(self):
        """Loop principal que roda em segundo plano."""
        while self.running:
            self.take_screenshot()
            # Espera o intervalo dividindo em pequenos passos para permitir parada rápida
            for _ in range(INTERVALO_SEGUNDOS): 
                if not self.running: break
                time.sleep(1)

    def open_settings(self, icon, item):
        """Abre a janela de configuração (GUI)."""
        root = as_tk.Tk()
        root.title("Configuração Monitor")
        root.geometry("400x200")
        
        lbl = as_tk.Label(root, text="Pasta de Destino (NAS):")
        lbl.pack(pady=5)
        
        entry_var = as_tk.StringVar(value=self.config.get("destination_path", ""))
        entry = as_tk.Entry(root, textvariable=entry_var, width=50)
        entry.pack(pady=5)
        
        def browse():
            d = filedialog.askdirectory()
            if d: entry_var.set(d)
            
        btn_browse = as_tk.Button(root, text="Selecionar Pasta", command=browse)
        btn_browse.pack(pady=5)
        
        # Checkbox Iniciar com Windows
        auto_start_var = as_tk.BooleanVar(value=self.config.get("auto_start", False))
        chk = as_tk.Checkbutton(root, text="Iniciar com o Windows", variable=auto_start_var)
        chk.pack(pady=10)

        def save():
            self.config["destination_path"] = entry_var.get()
            self.config["auto_start"] = auto_start_var.get()
            self.save_config()
            self.set_autostart(auto_start_var.get())
            messagebox.showinfo("Sucesso", "Configurações salvas!")
            root.destroy()
            
        btn_save = as_tk.Button(root, text="Salvar e Fechar", command=save, bg="#DDDDDD")
        btn_save.pack(pady=10)
        
        # Centralizar e focar
        root.eval('tk::PlaceWindow . center')
        root.mainloop()

    def exit_app(self, icon, item):
        self.running = False
        icon.stop()

    def run(self):
        # Inicia a thread de screenshots
        self.thread.start()
        
        # Configura o menu da bandeja
        menu = pystray.Menu(
            pystray.MenuItem('Configurar', self.open_settings),
            pystray.MenuItem('Sair', self.exit_app)
        )
        
        self.icon = pystray.Icon("Monitor", self.create_image(), "Monitor de Tela", menu)
        self.icon.run()

if __name__ == "__main__":
    app = MonitorApp()
    app.run()