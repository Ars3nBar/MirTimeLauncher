import os
import io
import json
import zipfile
import threading
import subprocess
import webbrowser
import requests
import customtkinter as ctk
import minecraft_launcher_lib as mclib

SERVER_IP = "mc.mir-time.ru"
BASE_DIR = os.path.join(os.getenv("APPDATA"), ".mirtime")
CONFIG_PATH = os.path.join(BASE_DIR, "launcher_config.json")

PROFILES = {
    "1.21.4 (Fabric + MTVisuals)": {
        "mc_version": "1.21.4",
        "folder": os.path.join(BASE_DIR, "1.21.4"),
        "mods": [
            {
                "name": "MTVisuals-1.0.0.jar",
                "zip_url": "https://github.com",
                "jar_inside": "MTVisuals-1.0.0.jar"
            },
            {"name": "fabric-api-1.21.4.jar", "modrinth_slug": "fabric-api", "mc": "1.21.4"},
            {"name": "sodium-1.21.4.jar", "modrinth_slug": "sodium", "mc": "1.21.4"}
        ]
    },
    "1.21.11 (Fabric)": {
        "mc_version": "1.21.11",
        "folder": os.path.join(BASE_DIR, "1.21.11"),
        "mods": [
            {"name": "fabric-api-1.21.11.jar", "modrinth_slug": "fabric-api", "mc": "1.21.11"},
            {"name": "sodium-1.21.11.jar", "modrinth_slug": "sodium", "mc": "1.21.11"}
        ]
    }
}

def load_cfg():
    os.makedirs(BASE_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"username": "Player", "ram_gb": 4, "profile": "1.21.4 (Fabric + MTVisuals)", "auto_connect": True}

def save_cfg(data):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def download_modrinth_latest(slug, mc_ver, dest_path):
    api = f"https://modrinth.com{slug}/version?loaders=%5B%22fabric%22%5D&game_versions=%5B%22{mc_ver}%22%5D"
    r = requests.get(api, timeout=15)
    if r.status_code == 200 and r.json():
        files = r.json().get("files", [])
        if files:
            dl_url = files["url"]
            with requests.get(dl_url, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                with open(dest_path, "wb") as out:
                    for chunk in resp.iter_content(chunk_size=65536):
                        out.write(chunk)
            return True
    return False
class MirTimeLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()

        ctk.set_appearance_mode("dark")
        self.title("MIR-TIME | Официальный Лаунчер")
        self.geometry("760x480")
        self.resizable(False, False)
        self.configure(fg_color="#090D16")

        header = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=14, border_width=1, border_color="#0055FF")
        header.pack(fill="x", padx=20, pady=(18, 12))

        ctk.CTkLabel(header, text="⚡ MIR-TIME LAUNCHER", font=("Segoe UI", 24, "bold"), text_color="#00E5FF").pack(side="left", padx=18, pady=12)
        ctk.CTkButton(header, text="Сайт / Донат", width=120, fg_color="#0055FF", hover_color="#0044CC",
                      command=lambda: webbrowser.open("https://mir-time.ru")).pack(side="right", padx=14)

        body = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=14, border_width=1, border_color="#1E293B")
        body.pack(fill="both", expand=True, padx=20, pady=6)

        ctk.CTkLabel(body, text="Игровой никнейм:", font=("Segoe UI", 14, "bold"), text_color="#E2E8F0").place(x=24, y=20)
        self.user_entry = ctk.CTkEntry(body, width=310, height=38, font=("Segoe UI", 14), fg_color="#090D16", border_color="#0055FF")
        self.user_entry.insert(0, self.cfg.get("username", "Player"))
        self.user_entry.place(x=24, y=50)

        ctk.CTkLabel(body, text="Версия клиента:", font=("Segoe UI", 14, "bold"), text_color="#E2E8F0").place(x=370, y=20)
        self.profile_box = ctk.CTkOptionMenu(
            body, width=320, height=38, font=("Segoe UI", 14, "bold"),
            values=list(PROFILES.keys()), fg_color="#0055FF", button_color="#0044CC"
        )
        saved_prof = self.cfg.get("profile", "1.21.4 (Fabric + MTVisuals)")
        if saved_prof in PROFILES:
            self.profile_box.set(saved_prof)
        self.profile_box.place(x=370, y=50)

        self.ram_label = ctk.CTkLabel(body, text=f"Выделение ОЗУ: {self.cfg.get('ram_gb', 4)} ГБ", font=("Segoe UI", 14, "bold"), text_color="#00FF66")
        self.ram_label.place(x=24, y=112)
        self.ram_slider = ctk.CTkSlider(body, from_=2, to=16, number_of_steps=14, width=310, progress_color="#00FF66", button_color="#00E5FF",
                                        command=self.on_ram_change)
        self.ram_slider.set(self.cfg.get("ram_gb", 4))
        self.ram_slider.place(x=24, y=145)

        self.auto_var = ctk.BooleanVar(value=self.cfg.get("auto_connect", True))
        self.auto_chk = ctk.CTkCheckBox(body, text=f"Сразу подключаться к {SERVER_IP}", variable=self.auto_var,
                                        font=("Segoe UI", 13), text_color="#CBD5E1", fg_color="#0055FF")
        self.auto_chk.place(x=370, y=125)

        ctk.CTkButton(body, text="📂 Папка игры", width=150, height=34, fg_color="#1E293B", hover_color="#334155",
                      command=self.open_game_folder).place(x=370, y=165)

        self.status_lbl = ctk.CTkLabel(body, text="Готов к запуску! Выберите версию и нажмите ИГРАТЬ.", font=("Segoe UI", 13), text_color="#94A3B8")
        self.status_lbl.place(x=24, y=220)

        self.progress = ctk.CTkProgressBar(body, width=666, height=14, progress_color="#00FF66", fg_color="#090D16")
        self.progress.set(0)
        self.progress.place(x=24, y=250)

        self.play_btn = ctk.CTkButton(
            body, text="▶ ИГРАТЬ НА MIR-TIME", width=666, height=52,
            font=("Segoe UI", 18, "bold"), fg_color="#00C853", hover_color="#00E676", text_color="#051B11",
            command=self.start_launch_thread
        )
        self.play_btn.place(x=24, y=282)

    def on_ram_change(self, val):
        self.ram_label.configure(text=f"Выделение ОЗУ: {int(val)} ГБ")

    def open_game_folder(self):
        prof = PROFILES[self.profile_box.get()]
        os.makedirs(prof["folder"], exist_ok=True)
        os.startfile(prof["folder"])

    def set_status(self, text, prog=None):
        self.after(0, lambda: self.status_lbl.configure(text=text))
        if prog is not None:
            self.after(0, lambda: self.progress.set(prog))

    def start_launch_thread(self):
        nick = self.user_entry.get().strip() or "Player"
        ram = int(self.ram_slider.get())
        prof_name = self.profile_box.get()
        auto_conn = self.auto_var.get()

        self.cfg = {"username": nick, "ram_gb": ram, "profile": prof_name, "auto_connect": auto_conn}
        save_cfg(self.cfg)

        self.play_btn.configure(state="disabled", text="⏳ ПОДГОТОВКА КЛИЕНТА...")
        threading.Thread(target=self.launch_game, args=(nick, ram, prof_name, auto_conn), daemon=True).start()

    def launch_game(self, nick, ram, prof_name, auto_conn):
        try:
            prof = PROFILES[prof_name]
            mc_ver = prof["mc_version"]
            mc_dir = prof["folder"]
            mods_dir = os.path.join(mc_dir, "mods")
            os.makedirs(mods_dir, exist_ok=True)

            callback = {
                "setStatus": lambda s: self.set_status(f"Загрузка: {s}"),
                "setProgress": lambda v: self.set_status(self.status_lbl.cget("text"), min(0.75, v / 100.0)),
                "setMax": lambda m: None
            }

            self.set_status(f"Установка Fabric {mc_ver} и Java...", 0.1)
            mclib.fabric.install_fabric(mc_ver, mc_dir, callback=callback)

            versions_dir = os.path.join(mc_dir, "versions")
            fabric_id = next((v for v in os.listdir(versions_dir) if "fabric-loader" in v and mc_ver in v), mc_ver)

            total_mods = len(prof["mods"])
            for idx, mod in enumerate(prof["mods"]):
                dest = os.path.join(mods_dir, mod["name"])
                self.set_status(f"Проверка мода {mod['name']}...", 0.75 + 0.2 * ((idx + 1) / total_mods))
                if "zip_url" in mod and not os.path.exists(dest):
                    try:
                        r = requests.get(mod["zip_url"], timeout=25)
                        if r.status_code == 200:
                            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                                data = zf.read(mod["jar_inside"])
                                with open(dest, "wb") as f:
                                    f.write(data)
                    except Exception:
                        pass
                elif "modrinth_slug" in mod and not os.path.exists(dest):
                    try:
                        download_modrinth_latest(mod["modrinth_slug"], mod["mc"], dest)
                    except Exception:
                        pass

            self.set_status(f"Запуск Minecraft {mc_ver}...", 1.0)
            options = {
                "username": nick,
                "uuid": "00000000-0000-0000-0000-000000000000",
                "token": "0",
                "jvmArguments": [f"-Xmx{ram}G", f"-Xms{max(1, ram // 2)}G"]
            }
            if auto_conn:
                options["server"] = SERVER_IP
                options["port"] = "25565"

            cmd = mclib.command.get_minecraft_command(fabric_id, mc_dir, options)
            subprocess.Popen(cmd, cwd=mc_dir)
            self.set_status(f"Игра запущена ({mc_ver})! Приятной игры на Mir-Time!", 1.0)
        except Exception as ex:
            self.set_status(f"Ошибка запуска: {ex}", 0.0)
        finally:
            self.after(0, lambda: self.play_btn.configure(state="normal", text="▶ ИГРАТЬ НА MIR-TIME"))

if __name__ == "__main__":
    app = MirTimeLauncher()
    app.mainloop()
