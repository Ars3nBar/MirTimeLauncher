import os
import io
import json
import math
import random
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

SERVERS = {
    "🇷🇺 РФ и СНГ • mc.mir-time.ru": "mc.mir-time.ru",
    "🇪🇺 Европа • eu.mir-time.ru": "eu.mir-time.ru"
}

LINKS = {
    "site": "https://mir-time.ru",
    "tg": "https://t.me",
    "vk": "https://vk.ru",
    "ds": "https://discord.gg"
}

LOGO_URL = "https://easydonate.ru"

BASE_DIR = os.path.join(os.getenv("APPDATA"), ".mirtime")
CONFIG_PATH = os.path.join(BASE_DIR, "launcher_config.json")

PROFILES = {
    "1.21.4": {
        "label": "⚡ 1.21.4 + MTVisuals",
        "sub": "Рекомендуемая • Сборка с фирменными визуалами",
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
    "1.21.11": {
        "label": "🚀 1.21.11 Fabric",
        "sub": "Новое ядро • Чистая оптимизированная сборка",
        "mc_version": "1.21.11",
        "folder": os.path.join(BASE_DIR, "1.21.11"),
        "core_mods": [
            {"name": "fabric-api-1.21.11.jar", "title": "Fabric API", "modrinth_slug": "fabric-api", "mc": "1.21.11"},
            {"name": "sodium-1.21.11.jar", "title": "Sodium (Буст FPS)", "modrinth_slug": "sodium", "mc": "1.21.11"}
        ]
    }
}

OPTIONAL_MODS = [
    {"id": "plasmovoice", "title": "Plasmo Voice (Голосовой чат)", "slug": "plasmo-voice"},
    {"id": "iris", "title": "Iris Shaders (Шейдеры)", "slug": "iris"},
    {"id": "lithium", "title": "Lithium (Оптимизация FPS)", "slug": "lithium"},
    {"id": "appleskin", "title": "AppleSkin (Индикатор еды)", "slug": "appleskin"},
    {"id": "modmenu", "title": "Mod Menu (Меню модов)", "slug": "modmenu"}
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
        "profile_key": "1.21.4",
        "server_label": "🇷🇺 РФ и СНГ • mc.mir-time.ru",
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
        versions = r.json()
        first_ver = next(iter(versions), None)
        if first_ver:
            files = first_ver.get("files", [])
            first_file = next(iter(files), None)
            if first_file and "url" in first_file:
                with requests.get(first_file.get("url"), stream=True, timeout=30) as resp:
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
        self.selected_profile = self.cfg.get("profile_key", "1.21.4")
        if self.selected_profile not in PROFILES:
            self.selected_profile = "1.21.4"

        self.anim_phase = 0.0
        self.target_progress = 0.0
        self.current_progress = 0.0
        self.last_loaded_nick = ""
        self._drag_x = 0
        self._drag_y = 0

        ctk.set_appearance_mode("dark")
        self.title("MIR-TIME LAUNCHER")
        self.geometry("900x610")
        self.overrideredirect(True)
        self.configure(fg_color="#04070F")

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"900x610+{(sw - 900) // 2}+{(sh - 610) // 2}")

        # Внешний неоновый корпус
        self.outer = ctk.CTkFrame(self, fg_color="#060B17", corner_radius=20, border_width=2, border_color="#0055FF")
        self.outer.pack(fill="both", expand=True, padx=2, pady=2)

        # Кастомная верхняя панель (Titlebar)
        self.titlebar = ctk.CTkFrame(self.outer, height=58, fg_color="#0A1226", corner_radius=15, border_width=1, border_color="#152342")
        self.titlebar.pack(fill="x", padx=14, pady=(12, 6))
        self.titlebar.bind("<Button-1>", self._start_move)
        self.titlebar.bind("<B1-Motion>", self._on_move)

        self.logo_icon_lbl = ctk.CTkLabel(self.titlebar, text="⚡", font=("Segoe UI", 24, "bold"), text_color="#00E5FF")
        self.logo_icon_lbl.pack(side="left", padx=(16, 8), pady=10)

        title_box = ctk.CTkFrame(self.titlebar, fg_color="transparent")
        title_box.pack(side="left", pady=6)
        t1 = ctk.CTkLabel(title_box, text="MIR-TIME LAUNCHER", font=("Segoe UI", 18, "bold"), text_color="#00E5FF")
        t1.pack(anchor="w")
        t2 = ctk.CTkLabel(title_box, text="CYBER ANARCHY EDITION • 1.21.4 — 1.21.11", font=("Segoe UI", 10, "bold"), text_color="#64748B")
        t2.pack(anchor="w")
        for w in (title_box, t1, t2):
            w.bind("<Button-1>", self._start_move)
            w.bind("<B1-Motion>", self._on_move)

        self.online_badge = ctk.CTkLabel(
            self.titlebar, text="● Пинг сервера...", font=("Segoe UI", 12, "bold"),
            fg_color="#0E1A36", corner_radius=10, padx=12, pady=5, text_color="#00FF66"
        )
        self.online_badge.pack(side="left", padx=18)

        ctk.CTkButton(
            self.titlebar, text="✕", width=36, height=32, corner_radius=10,
            fg_color="#162240", hover_color="#E11D48", font=("Segoe UI", 14, "bold"),
            command=self.destroy
        ).pack(side="right", padx=(4, 12))

        ctk.CTkButton(
            self.titlebar, text="—", width=36, height=32, corner_radius=10,
            fg_color="#162240", hover_color="#253663", font=("Segoe UI", 14, "bold"),
            command=self.iconify
        ).pack(side="right", padx=4)

        # Панель навигации и соцсетей (Сайт, ТГ, ВК, Discord)
        nav_bar = ctk.CTkFrame(self.outer, height=42, fg_color="#0A1226", corner_radius=13, border_width=1, border_color="#152342")
        nav_bar.pack(fill="x", padx=14, pady=4)

        ctk.CTkButton(
            nav_bar, text="🌐 Сайт и Донат", width=165, height=30, corner_radius=9,
            fg_color="#0055FF", hover_color="#0040C1", font=("Segoe UI", 12, "bold"),
            command=lambda: webbrowser.open(LINKS.get("site"))
        ).pack(side="left", padx=(10, 6), pady=6)

        ctk.CTkButton(
            nav_bar, text="✈ Telegram", width=130, height=30, corner_radius=9,
            fg_color="#0284C7", hover_color="#0369A1", font=("Segoe UI", 12, "bold"),
            command=lambda: webbrowser.open(LINKS.get("tg"))
        ).pack(side="left", padx=5, pady=6)

        ctk.CTkButton(
            nav_bar, text="💙 ВКонтакте", width=130, height=30, corner_radius=9,
            fg_color="#1D4ED8", hover_color="#1E40AF", font=("Segoe UI", 12, "bold"),
            command=lambda: webbrowser.open(LINKS.get("vk"))
        ).pack(side="left", padx=5, pady=6)

        ctk.CTkButton(
            nav_bar, text="💬 Discord", width=130, height=30, corner_radius=9,
            fg_color="#4F46E5", hover_color="#4338CA", font=("Segoe UI", 12, "bold"),
            command=lambda: webbrowser.open(LINKS.get("ds"))
        ).pack(side="left", padx=5, pady=6)

        ctk.CTkLabel(nav_bar, text="don.mir-time.ru", font=("Segoe UI", 12, "bold"), text_color="#00E5FF").pack(side="right", padx=14)

        # Вкладки
        self.tabs = ctk.CTkTabview(
            self.outer, width=870, height=350, corner_radius=15,
            fg_color="#0A1226", segmented_button_fg_color="#060B17",
            segmented_button_selected_color="#0055FF", segmented_button_selected_hover_color="#0040C1",
            segmented_button_unselected_color="#0E1A36", border_width=1, border_color="#152342"
        )
        self.tabs.pack(padx=14, pady=4)
        self.tab_play = self.tabs.add("🎮 Главная и Сборка")
        self.tab_mods = self.tabs.add("🧩 Менеджер модов")

        self.build_play_tab()
        self.build_mods_tab()
        # Нижняя панель с анимированным прогресс-баром
        self.footer = ctk.CTkFrame(self.outer, height=120, fg_color="#0A1226", corner_radius=15, border_width=1, border_color="#152342")
        self.footer.pack(fill="x", padx=14, pady=(6, 12))

        self.status_lbl = ctk.CTkLabel(
            self.footer, text="Готов к запуску! Выберите версию и нажмите ИГРАТЬ.",
            font=("Segoe UI", 13), text_color="#CBD5E1"
        )
        self.status_lbl.place(x=18, y=10)

        self.percent_lbl = ctk.CTkLabel(
            self.footer, text="0%", font=("Segoe UI", 15, "bold"), text_color="#00FF66"
        )
        self.percent_lbl.place(x=805, y=9)

        self.progress = ctk.CTkProgressBar(
            self.footer, width=834, height=14, corner_radius=7,
            progress_color="#00FF66", fg_color="#050811"
        )
        self.progress.set(0)
        self.progress.place(x=18, y=38)

        self.play_btn = ctk.CTkButton(
            self.footer, text="▶  ИГРАТЬ НА MIR-TIME", width=834, height=48, corner_radius=12,
            font=("Segoe UI", 18, "bold"), fg_color="#00C853", hover_color="#00E676", text_color="#04180E",
            command=self.start_launch_thread
        )
        self.play_btn.place(x=18, y=60)

        self.load_brand_logo()
        self.animate_ui()
        self.refresh_server_status()
        self.refresh_skin_avatar()

    def build_play_tab(self):
        # Левая карточка профиля со скином
        profile_card = ctk.CTkFrame(self.tab_play, width=245, height=280, corner_radius=15, fg_color="#070D1C", border_width=1, border_color="#152342")
        profile_card.place(x=10, y=8)

        self.avatar_lbl = ctk.CTkLabel(profile_card, text="🧑", font=("Segoe UI", 50), width=104, height=104, fg_color="#0E1A36", corner_radius=18)
        self.avatar_lbl.place(x=70, y=18)

        ctk.CTkLabel(profile_card, text="Игровой никнейм:", font=("Segoe UI", 12, "bold"), text_color="#94A3B8").place(x=20, y=132)
        self.user_entry = ctk.CTkEntry(profile_card, width=205, height=38, font=("Segoe UI", 14, "bold"), fg_color="#04070F", border_color="#0055FF")
        self.user_entry.insert(0, self.cfg.get("username", "Player"))
        self.user_entry.place(x=20, y=156)
        self.user_entry.bind("<FocusOut>", lambda e: self.refresh_skin_avatar())

        ctk.CTkButton(
            profile_card, text="🔄 Обновить превью скина", width=205, height=34, font=("Segoe UI", 12, "bold"),
            fg_color="#152342", hover_color="#1F3461", command=self.refresh_skin_avatar
        ).place(x=20, y=208)

        # Правая панель выбора версии и настроек
        right_card = ctk.CTkFrame(self.tab_play, width=590, height=280, corner_radius=15, fg_color="#070D1C", border_width=1, border_color="#152342")
        right_card.place(x=265, y=8)

        ctk.CTkLabel(right_card, text="Выберите версию клиента:", font=("Segoe UI", 13, "bold"), text_color="#E2E8F0").place(x=18, y=12)

        # Две интерактивные карточки версий (1.21.4 + MTVisuals и 1.21.11)
        self.ver_cards = {}
        ver_keys = list(PROFILES.keys())
        for idx, key in enumerate(ver_keys):
            p_info = PROFILES.get(key)
            card = ctk.CTkFrame(
                right_card, width=270, height=68, corner_radius=12,
                fg_color="#0E1A36", border_width=2, border_color="#0055FF"
            )
            card.place(x=18 + idx * 284, y=38)

            l1 = ctk.CTkLabel(card, text=p_info.get("label"), font=("Segoe UI", 14, "bold"), text_color="#00E5FF")
            l1.place(x=12, y=10)
            l2 = ctk.CTkLabel(card, text=p_info.get("sub"), font=("Segoe UI", 10), text_color="#94A3B8")
            l2.place(x=12, y=36)

            for w in (card, l1, l2):
                w.bind("<Button-1>", lambda e, k=key: self.select_profile(k))
            self.ver_cards[key] = card

        self.update_version_cards_style()

        # Шлюз и ОЗУ
        ctk.CTkLabel(right_card, text="Шлюз подключения:", font=("Segoe UI", 12, "bold"), text_color="#94A3B8").place(x=18, y=116)
        self.server_box = ctk.CTkOptionMenu(
            right_card, width=270, height=36, font=("Segoe UI", 12, "bold"),
            values=list(SERVERS.keys()), fg_color="#0E1A36", button_color="#1F3461"
        )
        saved_srv = self.cfg.get("server_label", "🇷🇺 РФ и СНГ • mc.mir-time.ru")
        if saved_srv in SERVERS:
            self.server_box.set(saved_srv)
        self.server_box.place(x=18, y=140)

        self.ram_label = ctk.CTkLabel(right_card, text=f"Выделение ОЗУ: {self.cfg.get('ram_gb', 4)} ГБ", font=("Segoe UI", 12, "bold"), text_color="#00FF66")
        self.ram_label.place(x=302, y=116)

        self.ram_slider = ctk.CTkSlider(
            right_card, from_=2, to=16, number_of_steps=14, width=270,
            progress_color="#00FF66", button_color="#00E5FF",
            command=lambda v: self.ram_label.configure(text=f"Выделение ОЗУ: {int(v)} ГБ")
        )
        self.ram_slider.set(self.cfg.get("ram_gb", 4))
        self.ram_slider.place(x=302, y=148)

        self.auto_var = ctk.BooleanVar(value=self.cfg.get("auto_connect", True))
        ctk.CTkCheckBox(
            right_card, text="Сразу заходить на сервер при запуске клиента",
            variable=self.auto_var, font=("Segoe UI", 13), text_color="#E2E8F0", fg_color="#0055FF"
        ).place(x=18, y=188)

        ctk.CTkButton(
            right_card, text="📂 Папка сборки", width=270, height=36, font=("Segoe UI", 13, "bold"),
            fg_color="#152342", hover_color="#1F3461", command=self.open_game_folder
        ).place(x=18, y=228)

        ctk.CTkButton(
            right_card, text="🧩 Настроить моды", width=270, height=36, font=("Segoe UI", 13, "bold"),
            fg_color="#0E1A36", hover_color="#152342", border_width=1, border_color="#00E5FF", text_color="#00E5FF",
            command=lambda: self.tabs.set("🧩 Менеджер модов")
        ).place(x=302, y=228)

    def select_profile(self, key):
        self.selected_profile = key
        self.update_version_cards_style()
        self.refresh_custom_mods_list()

    def update_version_cards_style(self):
        for k, card in self.ver_cards.items():
            if k == self.selected_profile:
                card.configure(fg_color="#102247", border_color="#00FF66")
            else:
                card.configure(fg_color="#0A1226", border_color="#1E2F57")

    def build_mods_tab(self):
        left = ctk.CTkFrame(self.tab_mods, width=410, height=280, corner_radius=15, fg_color="#070D1C", border_width=1, border_color="#152342")
        left.place(x=10, y=8)

        ctk.CTkLabel(left, text="Дополнительные моды (Modrinth):", font=("Segoe UI", 14, "bold"), text_color="#00E5FF").place(x=16, y=12)

        self.opt_vars = {}
        saved_opt = self.cfg.get("optional_mods", {})
        for idx, m in enumerate(OPTIONAL_MODS):
            var = ctk.BooleanVar(value=saved_opt.get(m.get("id"), True))
            self.opt_vars[m.get("id")] = var
            ctk.CTkCheckBox(
                left, text=m.get("title"), variable=var, font=("Segoe UI", 13),
                fg_color="#00FF66", checkmark_color="#04180E", text_color="#E2E8F0"
            ).place(x=18, y=50 + idx * 42)

        right = ctk.CTkFrame(self.tab_mods, width=420, height=280, corner_radius=15, fg_color="#070D1C", border_width=1, border_color="#152342")
        right.place(x=435, y=8)

        ctk.CTkLabel(right, text="Установленные моды сборки (.jar):", font=("Segoe UI", 14, "bold"), text_color="#00FF66").place(x=16, y=12)

        self.custom_mods_box = ctk.CTkTextbox(right, width=388, height=170, fg_color="#04070F", text_color="#CBD5E1", font=("Consolas", 12))
        self.custom_mods_box.place(x=16, y=46)

        ctk.CTkButton(
            right, text="➕ Добавить свой мод (.jar)", width=388, height=40, font=("Segoe UI", 13, "bold"),
            fg_color="#0055FF", hover_color="#0040C1", command=self.add_custom_mod
        ).place(x=16, y=226)

        self.refresh_custom_mods_list()
    def refresh_custom_mods_list(self):
        prof = PROFILES.get(self.selected_profile)
        mods_dir = os.path.join(prof.get("folder"), "mods")
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
        prof = PROFILES.get(self.selected_profile)
        mods_dir = os.path.join(prof.get("folder"), "mods")
        os.makedirs(mods_dir, exist_ok=True)
        for p in paths:
            shutil.copy2(p, os.path.join(mods_dir, os.path.basename(p)))
        self.refresh_custom_mods_list()
        self.set_status(f"Добавлено личных модов: {len(paths)} шт.", self.target_progress)

    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_move(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")

    def load_brand_logo(self):
        def worker():
            try:
                r = requests.get(LOGO_URL, timeout=10)
                if r.status_code == 200:
                    img = Image.open(io.BytesIO(r.content))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(36, 36))
                    self.after(0, lambda: self.logo_icon_lbl.configure(image=ctk_img, text=""))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def animate_ui(self):
        self.anim_phase += 0.08
        pulse = (math.sin(self.anim_phase) + 1) / 2
        if pulse < 0.33:
            col = "#0055FF"
            btn_col = "#00C853"
        elif pulse < 0.66:
            col = "#00E5FF"
            btn_col = "#00D65B"
        else:
            col = "#00FF66"
            btn_col = "#00E676"
        self.outer.configure(border_color=col)
        if self.play_btn.cget("state") == "normal":
            self.play_btn.configure(fg_color=btn_col)

        if abs(self.target_progress - self.current_progress) > 0.002:
            self.current_progress += (self.target_progress - self.current_progress) * 0.24
            self.progress.set(self.current_progress)
            self.percent_lbl.configure(text=f"{int(round(self.current_progress * 100))}%")

        self.after(45, self.animate_ui)

    def refresh_server_status(self):
        def worker():
            try:
                r = requests.get("https://mcsrvstat.us", timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("online"):
                        on = data.get("players", {}).get("online", 0)
                        mx = data.get("players", {}).get("max", 270)
                        self.after(0, lambda: self.online_badge.configure(text=f"● ОНЛАЙН: {on} / {mx}", text_color="#00FF66"))
                        return
            except Exception:
                pass
            self.after(0, lambda: self.online_badge.configure(text="● mc.mir-time.ru", text_color="#00E5FF"))
        threading.Thread(target=worker, daemon=True).start()

    def refresh_skin_avatar(self):
        nick = self.user_entry.get().strip() or "Steve"
        if nick == self.last_loaded_nick:
            return
        self.last_loaded_nick = nick
        def worker():
            try:
                r = requests.get(f"https://mc-heads.net{nick}/104", timeout=8)
                if r.status_code == 200:
                    img = Image.open(io.BytesIO(r.content))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(98, 98))
                    self.after(0, lambda: self.avatar_lbl.configure(image=ctk_img, text=""))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def open_game_folder(self):
        prof = PROFILES.get(self.selected_profile)
        os.makedirs(prof.get("folder"), exist_ok=True)
        os.startfile(prof.get("folder"))

    def set_status(self, text, prog=None):
        self.after(0, lambda: self.status_lbl.configure(text=text))
        if prog is not None:
            self.target_progress = max(0.0, min(1.0, float(prog)))

    def start_launch_thread(self):
        nick = self.user_entry.get().strip() or "Player"
        ram = int(self.ram_slider.get())
        prof_key = self.selected_profile
        srv_label = self.server_box.get()
        auto_conn = self.auto_var.get()
        opt_state = {k: v.get() for k, v in self.opt_vars.items()}

        self.cfg = {
            "username": nick, "ram_gb": ram, "profile_key": prof_key,
            "server_label": srv_label, "auto_connect": auto_conn, "optional_mods": opt_state
        }
        save_cfg(self.cfg)

        self.play_btn.configure(state="disabled", text="⏳  ПОДГОТОВКА И ЗАПУСК...")
        threading.Thread(target=self.launch_game, args=(nick, ram, prof_key, srv_label, auto_conn, opt_state), daemon=True).start()

    def launch_game(self, nick, ram, prof_key, srv_label, auto_conn, opt_state):
        try:
            prof = PROFILES.get(prof_key)
            mc_ver = prof.get("mc_version")
            mc_dir = prof.get("folder")
            mods_dir = os.path.join(mc_dir, "mods")
            os.makedirs(mods_dir, exist_ok=True)

            max_holder = {"max": 100}
            def set_max(m):
                if m > 0:
                    max_holder["max"] = m

            callback = {
                "setStatus": lambda s: self.set_status(f"Загрузка клиента: {s}"),
                "setProgress": lambda v: self.set_status(self.status_lbl.cget("text"), 0.05 + 0.65 * (v / max(1, max_holder.get("max")))),
                "setMax": set_max
            }

            self.set_status(f"Установка Fabric {mc_ver} и Java...", 0.05)
            mclib.fabric.install_fabric(mc_ver, mc_dir, callback=callback)

            versions_dir = os.path.join(mc_dir, "versions")
            fabric_id = next((v for v in os.listdir(versions_dir) if "fabric-loader" in v and mc_ver in v), mc_ver)

            tasks = list(prof.get("core_mods"))
            for om in OPTIONAL_MODS:
                if opt_state.get(om.get("id"), False):
                    tasks.append({
                        "name": f"{om.get('id')}-{mc_ver}.jar",
                        "title": om.get("title"),
                        "modrinth_slug": om.get("slug"),
                        "mc": mc_ver
                    })

            total = max(1, len(tasks))
            for idx, mod in enumerate(tasks):
                dest = os.path.join(mods_dir, mod.get("name"))
                prog = 0.70 + 0.28 * ((idx + 1) / total)
                self.set_status(f"Проверка мода: {mod.get('title')}...", prog)

                if "zip_url" in mod and not os.path.exists(dest):
                    try:
                        r = requests.get(mod.get("zip_url"), timeout=25)
                        if r.status_code == 200:
                            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                                with open(dest, "wb") as f:
                                    f.write(zf.read(mod.get("jar_inside")))
                    except Exception:
                        pass
                elif "modrinth_slug" in mod and not os.path.exists(dest):
                    try:
                        download_modrinth_latest(mod.get("modrinth_slug"), mod.get("mc"), dest)
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
                options["server"] = SERVERS.get(srv_label, "mc.mir-time.ru")
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
