import os
import time
import threading
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import pyautogui
from datetime import datetime
import sys
import subprocess
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
        self.icon = None
        # Carrega config inicial
        self.config = self.load_config()
        
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"destination_path": "", "auto_start": False}

    def create_image(self):
        """Gera ícone: Quadrado Azul com centro Branco"""
        width = 64
        height = 64
        color1 = (0, 120, 215)
        color2 = (255, 255, 255)
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=color2)
        return image

    def take_screenshot(self):
        # Recarrega a config a cada tentativa para pegar mudanças feitas na GUI
        current_config = self.load_config()
        path = current_config.get("destination_path")
        
        if not path or not os.path.exists(path):
            return 

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"screen_{timestamp}.png"
            fullpath = os.path.join(path, filename)
            
            screenshot = pyautogui.screenshot()
            screenshot.save(fullpath)
        except Exception as e:
            # Em produção silenciosa, erros não devem travar o app
            pass

    def loop_screenshots(self):
        """Loop que roda em thread separada (daemon)"""
        while self.running:
            self.take_screenshot()
            
            # Espera inteligente (permite sair rápido)
            for _ in range(INTERVALO_SEGUNDOS):
                if not self.running: return
                time.sleep(1)

    def launch_settings_process(self, icon, item):
        """
        TRUQUE: Em vez de abrir janela aqui e travar,
        lança uma nova instância do próprio executável com flag --config.
        Isso isola a GUI do TrayIcon.
        """
        executable = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        
        # Se estiver rodando como .exe (PyInstaller)
        if getattr(sys, 'frozen', False):
            subprocess.Popen([executable, "--config"])
        else:
            # Se estiver rodando como .py
            subprocess.Popen([executable, script_path, "--config"])

    def exit_app(self, icon, item):
        self.running = False
        icon.stop()
        os._exit(0) # Força bruta para matar threads pendentes

    def run_tray(self):
        # Inicia thread de screenshots
        t = threading.Thread(target=self.loop_screenshots)
        t.daemon = True # Garante que morre se o principal morrer
        t.start()
        
        # Menu da bandeja
        menu = pystray.Menu(
            pystray.MenuItem('Configurar', self.launch_settings_process),
            pystray.MenuItem('Sair', self.exit_app)
        )
        
        self.icon = pystray.Icon("Monitor", self.create_image(), "Monitor Ativo", menu)
        self.icon.run()

# --- Parte da Interface Gráfica (Roda em processo separado) ---
class ConfigWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Configuração Monitor")
        self.root.geometry("400x200")
        
        # Centraliza a janela
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (400 // 2)
        y = (screen_height // 2) - (200 // 2)
        self.root.geometry(f"400x200+{x}+{y}")
        
        self.config = self.load_config()
        self.build_ui()
        
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

    def set_autostart_registry(self, enable):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            # Detecta se é .exe ou .py para o registro
            if getattr(sys, 'frozen', False):
                exe_path = f'"{sys.executable}"'
            else:
                exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

            if enable:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro no registro: {e}")

    def build_ui(self):
        tk.Label(self.root, text="Pasta de Destino (NAS):").pack(pady=5)
        
        entry_var = tk.StringVar(value=self.config.get("destination_path", ""))
        tk.Entry(self.root, textvariable=entry_var, width=50).pack(pady=5)
        
        def browse():
            d = filedialog.askdirectory()
            if d: entry_var.set(d)
        
        tk.Button(self.root, text="...", command=browse).pack(pady=2)
        
        auto_start_var = tk.BooleanVar(value=self.config.get("auto_start", False))
        tk.Checkbutton(self.root, text="Iniciar com o Windows", variable=auto_start_var).pack(pady=10)

        def save():
            self.config["destination_path"] = entry_var.get()
            self.config["auto_start"] = auto_start_var.get()
            self.save_config()
            self.set_autostart_registry(auto_start_var.get())
            messagebox.showinfo("Sucesso", "Salvo! O monitor atualizará no próximo ciclo.")
            self.root.destroy()
            
        tk.Button(self.root, text="Salvar e Fechar", command=save, bg="#DDDDDD", height=2).pack(pady=10)
        self.root.mainloop()

# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    # Verifica se foi chamado com a flag --config
    if len(sys.argv) > 1 and sys.argv[1] == "--config":
        # MODO GUI: Abre apenas a janela de configuração
        ConfigWindow()
    else:
        # MODO TRAY: Inicia o monitoramento silencioso
        # Garante que só uma instância principal rode (opcional simples)
        app = MonitorApp()
        app.run_tray()