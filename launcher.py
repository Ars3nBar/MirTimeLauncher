import os
import io
import json
import math
import shutil
import zipfile
import threading
import subprocess
import webbrowser
from tkinter import filedialog
import requests
from PIL import Image
import customtkinter as ctk
import minecraft_launcher_lib as mclib

SERVER_IP = "mc.mir-time.ru"
BASE_DIR = os.path.join(os.getenv("APPDATA"), ".mirtime")
CONFIG_PATH = os.path.join(BASE_DIR, "launcher_config.json")

PROFILES = {
    "1.21.4 (Fabric + MTVisuals)": {
        "mc_version": "1.21.4",
        "folder": os.path.join(BASE_DIR, "1.21.4"),
        "core_mods": [
            {
                "name": "MTVisuals-1.0.0.jar",
                "title": "MTVisuals (Фирменные визуалы)",
                "zip_url": "https://github.com",
                "jar_inside": "MTVisuals-1.0.0.jar"
            },
            {"name": "fabric-api-1.21.4.jar", "title": "Fabric API", "modrinth_slug": "fabric-api", "mc": "1.21.4"},
            {"name": "sodium-1.21.4.jar", "title": "Sodium (Буст FPS)", "modrinth_slug": "sodium", "mc": "1.21.4"}
        ]
    },
    "1.21.11 (Fabric)": {
        "mc_version": "1.21.11",
        "folder": os.path.join(BASE_DIR, "1.21.11"),
        "core_mods": [
            {"name": "fabric-api-1.21.11.jar", "title": "Fabric API", "modrinth_slug": "fabric-api", "mc": "1.21.11"},
            {"name": "sodium-1.21.11.jar", "title": "Sodium (Буст FPS)", "modrinth_slug": "sodium", "mc": "1.21.11"}
        ]
    }
}

OPTIONAL_MODS = [
    {"id": "plasmovoice", "title": "Plasmo Voice (Голосовой чат в игре)", "slug": "plasmo-voice"},
    {"id": "iris", "title": "Iris Shaders (Поддержка шейдеров)", "slug": "iris"},
    {"id": "lithium", "title": "Lithium (Оптимизация физики и TPS)", "slug": "lithium"},
    {"id": "appleskin", "title": "AppleSkin (Показ насыщения еды)", "slug": "appleskin"},
    {"id": "modmenu", "title": "Mod Menu (Список модов в меню)", "slug": "modmenu"}
]

def load_cfg():
    os.makedirs(BASE_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "username": "Player",
        "ram_gb": 4,
        "profile": "1.21.4 (Fabric + MTVisuals)",
        "auto_connect": True,
        "optional_mods": {"plasmovoice": True, "iris": False, "lithium": True, "appleskin": True, "modmenu": True}
    }

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
        self.anim_phase = 0.0
        self.target_progress = 0.0
        self.current_progress = 0.0
        self.last_loaded_nick = ""

        ctk.set_appearance_mode("dark")
        self.title("MIR-TIME | Официальный Лаунчер v2.0")
        self.geometry("820x540")
        self.resizable(False, False)
        self.configure(fg_color="#070B14")

        # Шапка с неоновой обводкой
        self.header = ctk.CTkFrame(self, fg_color="#0D1526", corner_radius=16, border_width=2, border_color="#0055FF")
        self.header.pack(fill="x", padx=20, pady=(16, 10))

        self.logo_lbl = ctk.CTkLabel(self.header, text="⚡ MIR-TIME LAUNCHER", font=("Segoe UI", 23, "bold"), text_color="#00E5FF")
        self.logo_lbl.pack(side="left", padx=18, pady=12)

        self.online_badge = ctk.CTkLabel(
            self.header, text="● Проверка сервера...", font=("Segoe UI", 12, "bold"),
            fg_color="#111C33", corner_radius=10, padx=12, pady=5, text_color="#94A3B8"
        )
        self.online_badge.pack(side="left", padx=8)

        ctk.CTkButton(
            self.header, text="🌐 Сайт / Донат", width=130, height=34, font=("Segoe UI", 13, "bold"),
            fg_color="#0055FF", hover_color="#0040C1", command=lambda: webbrowser.open("https://mir-time.ru")
        ).pack(side="right", padx=14)

        # Переключатель вкладок (Главная / Менеджер модов)
        self.tabs = ctk.CTkTabview(
            self, width=780, height=315, corner_radius=14,
            fg_color="#0D1526", segmented_button_fg_color="#070B14",
            segmented_button_selected_color="#0055FF", segmented_button_selected_hover_color="#0040C1",
            segmented_button_unselected_color="#111C33", border_width=1, border_color="#1E293B"
        )
        self.tabs.pack(padx=20, pady=4)
        self.tab_play = self.tabs.add("🎮 Запуск игры")
        self.tab_mods = self.tabs.add("🧩 Менеджер модов")

        self.build_play_tab()
        self.build_mods_tab()

        # Нижняя панель прогресса и кнопка ИГРАТЬ
        self.footer = ctk.CTkFrame(self, fg_color="#0D1526", corner_radius=16, border_width=1, border_color="#1E293B")
        self.footer.pack(fill="x", padx=20, pady=(8, 16))

        self.status_lbl = ctk.CTkLabel(
            self.footer, text="Готов к запуску! Выберите профиль и нажмите ИГРАТЬ.",
            font=("Segoe UI", 13), text_color="#CBD5E1"
        )
        self.status_lbl.place(x=18, y=10)

        self.percent_lbl = ctk.CTkLabel(
            self.footer, text="0%", font=("Segoe UI", 14, "bold"), text_color="#00FF66"
        )
        self.percent_lbl.place(x=725, y=10)

        self.progress = ctk.CTkProgressBar(
            self.footer, width=744, height=14, corner_radius=7,
            progress_color="#00FF66", fg_color="#070B14"
        )
        self.progress.set(0)
        self.progress.place(x=18, y=38)

        self.play_btn = ctk.CTkButton(
            self.footer, text="▶  ИГРАТЬ НА MIR-TIME", width=744, height=48, corner_radius=12,
            font=("Segoe UI", 18, "bold"), fg_color="#00C853", hover_color="#00E676", text_color="#04180E",
            command=self.start_launch_thread
        )
        self.play_btn.place(x=18, y=60)
        self.footer.configure(height=120)

        self.animate_ui()
        self.refresh_server_status()
        self.refresh_skin_avatar()

    def build_play_tab(self):
        # Карточка профиля слева со скином
        profile_card = ctk.CTkFrame(self.tab_play, width=230, height=245, corner_radius=14, fg_color="#090F1D", border_width=1, border_color="#1E293B")
        profile_card.place(x=14, y=10)

        self.avatar_lbl = ctk.CTkLabel(profile_card, text="🧑", font=("Segoe UI", 48), width=96, height=96, fg_color="#111C33", corner_radius=14)
        self.avatar_lbl.place(x=67, y=18)

        ctk.CTkLabel(profile_card, text="Ваш игровой ник:", font=("Segoe UI", 12, "bold"), text_color="#94A3B8").place(x=20, y=126)
        self.user_entry = ctk.CTkEntry(profile_card, width=190, height=36, font=("Segoe UI", 14, "bold"), fg_color="#070B14", border_color="#0055FF")
        self.user_entry.insert(0, self.cfg.get("username", "Player"))
        self.user_entry.place(x=20, y=150)
        self.user_entry.bind("<FocusOut>", lambda e: self.refresh_skin_avatar())

        ctk.CTkButton(
            profile_card, text="Обновить скин", width=190, height=30, font=("Segoe UI", 12),
            fg_color="#1E293B", hover_color="#334155", command=self.refresh_skin_avatar
        ).place(x=20, y=198)

        # Настройки клиента справа
        settings_card = ctk.CTkFrame(self.tab_play, width=500, height=245, corner_radius=14, fg_color="#090F1D", border_width=1, border_color="#1E293B")
        settings_card.place(x=256, y=10)

        ctk.CTkLabel(settings_card, text="Версия клиента и сборка:", font=("Segoe UI", 14, "bold"), text_color="#E2E8F0").place(x=20, y=16)
        self.profile_box = ctk.CTkOptionMenu(
            settings_card, width=460, height=40, font=("Segoe UI", 14, "bold"),
            values=list(PROFILES.keys()), fg_color="#0055FF", button_color="#0040C1",
            command=lambda _: self.refresh_custom_mods_list()
        )
        saved_prof = self.cfg.get("profile", "1.21.4 (Fabric + MTVisuals)")
        if saved_prof in PROFILES:
            self.profile_box.set(saved_prof)
        self.profile_box.place(x=20, y=46)

        self.ram_label = ctk.CTkLabel(settings_card, text=f"Оперативная память (RAM): {self.cfg.get('ram_gb', 4)} ГБ", font=("Segoe UI", 14, "bold"), text_color="#00FF66")
        self.ram_label.place(x=20, y=102)

        self.ram_slider = ctk.CTkSlider(
            settings_card, from_=2, to=16, number_of_steps=14, width=460,
            progress_color="#00FF66", button_color="#00E5FF",
            command=lambda v: self.ram_label.configure(text=f"Оперативная память (RAM): {int(v)} ГБ")
        )
        self.ram_slider.set(self.cfg.get("ram_gb", 4))
        self.ram_slider.place(x=20, y=134)

        self.auto_var = ctk.BooleanVar(value=self.cfg.get("auto_connect", True))
        ctk.CTkCheckBox(
            settings_card, text=f"Автовход на сервер {SERVER_IP} при запуске",
            variable=self.auto_var, font=("Segoe UI", 13), text_color="#E2E8F0", fg_color="#0055FF"
        ).place(x=20, y=170)

        ctk.CTkButton(
            settings_card, text="📂 Открыть папку сборки", width=220, height=34, font=("Segoe UI", 13),
            fg_color="#1E293B", hover_color="#334155", command=self.open_game_folder
        ).place(x=20, y=202)

        ctk.CTkButton(
            settings_card, text="🧩 Настроить моды", width=220, height=34, font=("Segoe UI", 13, "bold"),
            fg_color="#111C33", hover_color="#1E293B", border_width=1, border_color="#00E5FF", text_color="#00E5FF",
            command=lambda: self.tabs.set("🧩 Менеджер модов")
        ).place(x=260, y=202)
    def build_mods_tab(self):
        left = ctk.CTkFrame(self.tab_mods, width=375, height=245, corner_radius=14, fg_color="#090F1D", border_width=1, border_color="#1E293B")
        left.place(x=14, y=10)

        ctk.CTkLabel(left, text="Дополнительные моды (Modrinth):", font=("Segoe UI", 14, "bold"), text_color="#00E5FF").place(x=16, y=12)

        self.opt_vars = {}
        saved_opt = self.cfg.get("optional_mods", {})
        for idx, m in enumerate(OPTIONAL_MODS):
            var = ctk.BooleanVar(value=saved_opt.get(m["id"], True))
            self.opt_vars[m["id"]] = var
            ctk.CTkCheckBox(
                left, text=m["title"], variable=var, font=("Segoe UI", 13),
                fg_color="#00FF66", checkmark_color="#04180E", text_color="#E2E8F0"
            ).place(x=18, y=46 + idx * 36)

        right = ctk.CTkFrame(self.tab_mods, width=360, height=245, corner_radius=14, fg_color="#090F1D", border_width=1, border_color="#1E293B")
        right.place(x=400, y=10)

        ctk.CTkLabel(right, text="Ваши личные моды (.jar):", font=("Segoe UI", 14, "bold"), text_color="#00FF66").place(x=16, y=12)

        self.custom_mods_box = ctk.CTkTextbox(right, width=328, height=140, fg_color="#070B14", text_color="#CBD5E1", font=("Consolas", 12))
        self.custom_mods_box.place(x=16, y=44)

        ctk.CTkButton(
            right, text="➕ Добавить свой мод (.jar)", width=328, height=38, font=("Segoe UI", 13, "bold"),
            fg_color="#0055FF", hover_color="#0040C1", command=self.add_custom_mod
        ).place(x=16, y=194)

        self.refresh_custom_mods_list()

    def refresh_custom_mods_list(self):
        prof = PROFILES[self.profile_box.get()]
        mods_dir = os.path.join(prof["folder"], "mods")
        os.makedirs(mods_dir, exist_ok=True)
        files = [f for f in os.listdir(mods_dir) if f.endswith(".jar")]
        self.custom_mods_box.configure(state="normal")
        self.custom_mods_box.delete("1.0", "end")
        if not files:
            self.custom_mods_box.insert("end", "Папка модов пока пуста.\nНажмите ИГРАТЬ, чтобы скачать сборку,\nили добавьте свои .jar кнопкой ниже.")
        else:
            for f in sorted(files):
                self.custom_mods_box.insert("end", f"✔ {f}\n")
        self.custom_mods_box.configure(state="disabled")

    def add_custom_mod(self):
        paths = filedialog.askopenfilenames(title="Выберите файлы модов (.jar)", filetypes=[("Minecraft Mods", "*.jar")])
        if not paths:
            return
        prof = PROFILES[self.profile_box.get()]
        mods_dir = os.path.join(prof["folder"], "mods")
        os.makedirs(mods_dir, exist_ok=True)
        for p in paths:
            shutil.copy2(p, os.path.join(mods_dir, os.path.basename(p)))
        self.refresh_custom_mods_list()
        self.set_status(f"Добавлено модов в сборку: {len(paths)} шт.", self.target_progress)

    def animate_ui(self):
        self.anim_phase += 0.08
        pulse = (math.sin(self.anim_phase) + 1) / 2  # 0.0 .. 1.0
        border_col = "#0055FF" if pulse < 0.5 else "#00E5FF"
        self.header.configure(border_color=border_col)

        # Плавное скольжение прогресс-бара и процентов
        if abs(self.target_progress - self.current_progress) > 0.002:
            self.current_progress += (self.target_progress - self.current_progress) * 0.22
            self.progress.set(self.current_progress)
            self.percent_lbl.configure(text=f"{int(round(self.current_progress * 100))}%")

        self.after(45, self.animate_ui)

    def refresh_server_status(self):
        def worker():
            try:
                r = requests.get(f"https://mcsrvstat.us{SERVER_IP}", timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("online"):
                        on = data.get("players", {}).get("online", 0)
                        mx = data.get("players", {}).get("max", 270)
                        self.after(0, lambda: self.online_badge.configure(text=f"● ОНЛАЙН: {on} / {mx}", text_color="#00FF66"))
                        return
            except Exception:
                pass
            self.after(0, lambda: self.online_badge.configure(text=f"● {SERVER_IP}", text_color="#00E5FF"))
        threading.Thread(target=worker, daemon=True).start()

    def refresh_skin_avatar(self):
        nick = self.user_entry.get().strip() or "Steve"
        if nick == self.last_loaded_nick:
            return
        self.last_loaded_nick = nick
        def worker():
            try:
                r = requests.get(f"https://mc-heads.net{nick}/96", timeout=8)
                if r.status_code == 200:
                    img = Image.open(io.BytesIO(r.content))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(92, 92))
                    self.after(0, lambda: self.avatar_lbl.configure(image=ctk_img, text=""))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def open_game_folder(self):
        prof = PROFILES[self.profile_box.get()]
        os.makedirs(prof["folder"], exist_ok=True)
        os.startfile(prof["folder"])

    def set_status(self, text, prog=None):
        self.after(0, lambda: self.status_lbl.configure(text=text))
        if prog is not None:
            self.target_progress = max(0.0, min(1.0, float(prog)))

    def start_launch_thread(self):
        nick = self.user_entry.get().strip() or "Player"
        ram = int(self.ram_slider.get())
        prof_name = self.profile_box.get()
        auto_conn = self.auto_var.get()
        opt_state = {k: v.get() for k, v in self.opt_vars.items()}

        self.cfg = {
            "username": nick, "ram_gb": ram, "profile": prof_name,
            "auto_connect": auto_conn, "optional_mods": opt_state
        }
        save_cfg(self.cfg)

        self.play_btn.configure(state="disabled", text="⏳  ЗАГРУЗКА И ЗАПУСК...")
        threading.Thread(target=self.launch_game, args=(nick, ram, prof_name, auto_conn, opt_state), daemon=True).start()

    def launch_game(self, nick, ram, prof_name, auto_conn, opt_state):
        try:
            prof = PROFILES[prof_name]
            mc_ver = prof["mc_version"]
            mc_dir = prof["folder"]
            mods_dir = os.path.join(mc_dir, "mods")
            os.makedirs(mods_dir, exist_ok=True)

            max_val = [100]
            def set_max(m):
                if m > 0:
                    max_val = m

            callback = {
                "setStatus": lambda s: self.set_status(f"Установка клиента: {s}"),
                "setProgress": lambda v: self.set_status(self.status_lbl.cget("text"), 0.05 + 0.65 * (v / max(1, max_val))),
                "setMax": set_max
            }

            self.set_status(f"Проверка ядра Fabric {mc_ver} и Java...", 0.05)
            mclib.fabric.install_fabric(mc_ver, mc_dir, callback=callback)

            versions_dir = os.path.join(mc_dir, "versions")
            fabric_id = next((v for v in os.listdir(versions_dir) if "fabric-loader" in v and mc_ver in v), mc_ver)

            # Собираем список всех нужных модов (базовые + выбранные опциональные)
            tasks = list(prof["core_mods"])
            for om in OPTIONAL_MODS:
                if opt_state.get(om["id"], False):
                    tasks.append({
                        "name": f"{om['id']}-{mc_ver}.jar",
                        "title": om["title"],
                        "modrinth_slug": om["slug"],
                        "mc": mc_ver
                    })

            total = max(1, len(tasks))
            for idx, mod in enumerate(tasks):
                dest = os.path.join(mods_dir, mod["name"])
                prog = 0.70 + 0.28 * ((idx + 1) / total)
                self.set_status(f"Загрузка мода: {mod['title']}...", prog)

                if "zip_url" in mod and not os.path.exists(dest):
                    try:
                        r = requests.get(mod["zip_url"], timeout=25)
                        if r.status_code == 200:
                            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                                with open(dest, "wb") as f:
                                    f.write(zf.read(mod["jar_inside"]))
                    except Exception:
                        pass
                elif "modrinth_slug" in mod and not os.path.exists(dest):
                    try:
                        download_modrinth_latest(mod["modrinth_slug"], mod["mc"], dest)
                    except Exception:
                        pass

            self.after(0, self.refresh_custom_mods_list)
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
            self.set_status(f"✔ Игра запущена ({mc_ver})! Приятной игры на Mir-Time!", 1.0)
        except Exception as ex:
            self.set_status(f"Ошибка запуска: {ex}", 0.0)
        finally:
            self.after(0, lambda: self.play_btn.configure(state="normal", text="▶  ИГРАТЬ НА MIR-TIME"))

if __name__ == "__main__":
    app = MirTimeLauncher()
    app.mainloop()
