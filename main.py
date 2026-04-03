import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, colorchooser
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import os
import sys
import logging
import traceback
import json
import time

# Logging Configuration
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

LOG_FILE = get_resource_path("logs.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

# Localization Loader
LANG_DATA = {}
def load_translations(lang):
    global LANG_DATA
    lang_file = get_resource_path(os.path.join("Localization", f"{lang}.json"))
    if os.path.exists(lang_file):
        try:
            with open(lang_file, 'r', encoding='utf-8-sig') as f:
                LANG_DATA = json.load(f)
        except Exception as e:
            logging.error(f"Error loading translation {lang}: {e}")
            LANG_DATA = {}
    else:
        logging.error(f"Translation file not found: {lang_file}")
        LANG_DATA = {}

def get_text(key):
    return LANG_DATA.get(key, key)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    # Show message to user
    try:
        title = get_text("msg_error")
        msg = get_text("error_critical").format(os.path.basename(LOG_FILE), exc_value)
        messagebox.showerror(title, msg)
    except:
        pass

sys.excepthook = handle_exception

# Add current path to import core
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core import VideoProcessor

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.lang = "it-IT"
        load_translations(self.lang)

        self.title(get_text("title"))
        self.geometry("1200x800")
        
        # Set icon
        try:
            icon_path = get_resource_path("favicon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            logging.error(f"Error setting icon: {e}")
        
        self.processor = None
        self.preview_frame_idx = 0
        self.is_converting = False
        self.is_playing = False
        self.last_preview_frame = None
        self.stop_event = threading.Event()
        self.play_thread = None
        self.target_frame_selector = "start" # "start" or "end"
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False) # Fixed width
        
        # Tabview for sidebar instead of just scrollable frame
        self.tabview = ctk.CTkTabview(self.sidebar, width=300)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_video = self.tabview.add(get_text("tab_video"))
        self.tab_auto = self.tabview.add(get_text("tab_auto"))
        self.tab_manual = self.tabview.add(get_text("tab_manual"))
        self.tab_midi = self.tabview.add(get_text("tab_midi"))

        # --- TAB VIDEO ---
        self.load_btn = ctk.CTkButton(self.tab_video, text=get_text("load_video"), command=self.load_video)
        self.load_btn.pack(pady=10, padx=10, fill="x")

        self.frames_label = ctk.CTkLabel(self.tab_video, text=get_text("start_frame_label"))
        self.frames_label.pack(pady=(10, 0))
        
        self.frames_frame = ctk.CTkFrame(self.tab_video, fg_color="transparent")
        self.frames_frame.pack(pady=5, padx=10, fill="x")
        
        self.play_btn = ctk.CTkButton(self.frames_frame, text="▶", width=30, command=self.toggle_play)
        self.play_btn.pack(side="left", padx=2)

        self.start_frame_entry = ctk.CTkEntry(self.frames_frame, width=80)
        self.start_frame_entry.insert(0, "0")
        self.start_frame_entry.pack(side="left", expand=True, padx=2)
        self.start_frame_entry.bind("<FocusOut>", lambda e: self.update_frame_indices())
        self.start_frame_entry.bind("<Return>", lambda e: self.update_frame_indices())
        self.start_frame_entry.bind("<FocusIn>", lambda e: self.set_target_selector("start"))
        
        self.end_frame_entry = ctk.CTkEntry(self.frames_frame, width=80)
        self.end_frame_entry.insert(0, "0")
        self.end_frame_entry.pack(side="left", expand=True, padx=2)
        self.end_frame_entry.bind("<FocusOut>", lambda e: self.update_frame_indices())
        self.end_frame_entry.bind("<Return>", lambda e: self.update_frame_indices())
        self.end_frame_entry.bind("<FocusIn>", lambda e: self.set_target_selector("end"))

        self.play_hint = ctk.CTkLabel(self.tab_video, text=get_text("play_hint"), font=ctk.CTkFont(size=10), wraplength=250)
        self.play_hint.pack(pady=5, padx=10)

        # --- TAB AUTO ---
        self.height_slider_label = ctk.CTkLabel(self.tab_auto, text=get_text("height_label"))
        self.height_slider_label.pack(pady=(10, 0))
        self.height_slider = ctk.CTkSlider(self.tab_auto, from_=0, to=1, command=self.update_height)
        self.height_slider.set(0.75)
        self.height_slider.pack(pady=10, padx=10, fill="x")

        self.area_slider_label = ctk.CTkLabel(self.tab_auto, text=get_text("area_label"))
        self.area_slider_label.pack(pady=(10, 0))
        self.area_slider = ctk.CTkSlider(self.tab_auto, from_=1, to=50, command=self.update_detection_height)
        self.area_slider.set(10)
        self.area_slider.pack(pady=10, padx=10, fill="x")

        self.threshold_slider_label = ctk.CTkLabel(self.tab_auto, text=get_text("threshold_label"))
        self.threshold_slider_label.pack(pady=(10, 0))
        self.threshold_slider = ctk.CTkSlider(self.tab_auto, from_=1, to=100, command=self.update_threshold)
        self.threshold_slider.set(30)
        self.threshold_slider.pack(pady=10, padx=10, fill="x")

        self.advanced_label = ctk.CTkLabel(self.tab_auto, text=get_text("sensitivity_label"))
        self.advanced_label.pack(pady=(10, 0))
        
        self.sensitivity_frame = ctk.CTkFrame(self.tab_auto, fg_color="transparent")
        self.sensitivity_frame.pack(pady=5, padx=10, fill="x")
        
        self.white_sens = ctk.CTkEntry(self.sensitivity_frame, width=60, placeholder_text=get_text("white_placeholder"))
        self.white_sens.insert(0, "0.7")
        self.white_sens.pack(side="left", expand=True, padx=2)
        
        self.black_sens = ctk.CTkEntry(self.sensitivity_frame, width=60, placeholder_text=get_text("black_placeholder"))
        self.black_sens.insert(0, "0.3")
        self.black_sens.pack(side="right", expand=True, padx=2)

        # --- TAB MANUAL ---
        self.manual_switch = ctk.CTkSwitch(self.tab_manual, text=get_text("manual_mode_switch"), command=self.toggle_manual_mode)
        self.manual_switch.pack(pady=10, padx=10)
        
        self.manual_hint = ctk.CTkLabel(self.tab_manual, text=get_text("manual_mode_hint"), font=ctk.CTkFont(size=10), wraplength=250)
        self.manual_hint.pack(pady=5, padx=10)

        self.note_names_switch = ctk.CTkSwitch(self.tab_manual, text=get_text("note_names_switch"), command=self.toggle_note_names)
        self.note_names_switch.pack(pady=5, padx=10)

        self.start_key_label = ctk.CTkLabel(self.tab_manual, text=get_text("start_key_label"))
        self.start_key_label.pack(pady=(10, 0))
        self.start_key_entry = ctk.CTkEntry(self.tab_manual)
        self.start_key_entry.insert(0, "21")
        self.start_key_entry.pack(pady=10, padx=10, fill="x")
        self.start_key_entry.bind("<FocusOut>", lambda e: self.update_preview())
        self.start_key_entry.bind("<Return>", lambda e: self.update_preview())

        # --- TAB MIDI ---
        self.bpm_label = ctk.CTkLabel(self.tab_midi, text=get_text("bpm_label"))
        self.bpm_label.pack(pady=(10, 0))
        self.bpm_entry = ctk.CTkEntry(self.tab_midi)
        self.bpm_entry.insert(0, "120")
        self.bpm_entry.pack(pady=10, padx=10, fill="x")

        self.quantize_frame = ctk.CTkFrame(self.tab_midi, fg_color="transparent")
        self.quantize_frame.pack(pady=5, padx=10, fill="x")
        
        self.quantize_switch = ctk.CTkSwitch(self.quantize_frame, text=get_text("quantize_switch"))
        self.quantize_switch.pack(side="left", padx=(0, 10))
        
        self.quantize_value = ctk.CTkOptionMenu(self.quantize_frame, values=["1/1", "1/2", "1/4", "1/8", "1/16", "1/32", "1/64"], width=80)
        self.quantize_value.set("1/16")
        self.quantize_value.pack(side="right")

        # --- TAB FILTER ---
        self.tab_filter = self.tabview.add(get_text("tab_filter"))
        
        # Sub-tabs for filters
        self.filter_tabs = ctk.CTkTabview(self.tab_filter, width=280, height=350)
        self.filter_tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.sub_hsv = self.filter_tabs.add(get_text("subtab_hsv"))
        self.sub_adjust = self.filter_tabs.add(get_text("subtab_adjust"))
        self.sub_noise = self.filter_tabs.add(get_text("subtab_noise"))

        self.filter_switch = ctk.CTkSwitch(self.tab_filter, text=get_text("filter_switch"), command=self.update_filter_params)
        self.filter_switch.pack(pady=(0, 5), padx=10)

        # --- SUBTAB HSV ---
        # Hue
        self.hue_label = ctk.CTkLabel(self.sub_hsv, text=get_text("hue_range"))
        self.hue_label.pack(pady=(5, 0))
        
        self.hue_min_label = ctk.CTkLabel(self.sub_hsv, text=get_text("min_label"), font=ctk.CTkFont(size=10))
        self.hue_min_label.pack(pady=0)
        self.hue_min_slider = ctk.CTkSlider(self.sub_hsv, from_=0, to=180, command=self.update_filter_params)
        self.hue_min_slider.set(0)
        self.hue_min_slider.pack(pady=2, padx=10, fill="x")
        
        self.hue_max_label = ctk.CTkLabel(self.sub_hsv, text=get_text("max_label"), font=ctk.CTkFont(size=10))
        self.hue_max_label.pack(pady=0)
        self.hue_max_slider = ctk.CTkSlider(self.sub_hsv, from_=0, to=180, command=self.update_filter_params)
        self.hue_max_slider.set(180)
        self.hue_max_slider.pack(pady=2, padx=10, fill="x")

        # Saturation
        self.sat_label = ctk.CTkLabel(self.sub_hsv, text=get_text("sat_range"))
        self.sat_label.pack(pady=(5, 0))
        
        self.sat_min_label = ctk.CTkLabel(self.sub_hsv, text=get_text("min_label"), font=ctk.CTkFont(size=10))
        self.sat_min_label.pack(pady=0)
        self.sat_min_slider = ctk.CTkSlider(self.sub_hsv, from_=0, to=255, command=self.update_filter_params)
        self.sat_min_slider.set(0)
        self.sat_min_slider.pack(pady=2, padx=10, fill="x")
        
        self.sat_max_label = ctk.CTkLabel(self.sub_hsv, text=get_text("max_label"), font=ctk.CTkFont(size=10))
        self.sat_max_label.pack(pady=0)
        self.sat_max_slider = ctk.CTkSlider(self.sub_hsv, from_=0, to=255, command=self.update_filter_params)
        self.sat_max_slider.set(255)
        self.sat_max_slider.pack(pady=2, padx=10, fill="x")

        # Value (Brightness)
        self.val_label = ctk.CTkLabel(self.sub_hsv, text=get_text("val_range"))
        self.val_label.pack(pady=(5, 0))
        
        self.val_min_label = ctk.CTkLabel(self.sub_hsv, text=get_text("min_label"), font=ctk.CTkFont(size=10))
        self.val_min_label.pack(pady=0)
        self.val_min_slider = ctk.CTkSlider(self.sub_hsv, from_=0, to=255, command=self.update_filter_params)
        self.val_min_slider.set(0)
        self.val_min_slider.pack(pady=2, padx=10, fill="x")
        
        self.val_max_label = ctk.CTkLabel(self.sub_hsv, text=get_text("max_label"), font=ctk.CTkFont(size=10))
        self.val_max_label.pack(pady=0)
        self.val_max_slider = ctk.CTkSlider(self.sub_hsv, from_=0, to=255, command=self.update_filter_params)
        self.val_max_slider.set(255)
        self.val_max_slider.pack(pady=2, padx=10, fill="x")

        # --- SUBTAB ADJUST ---
        # Contrast
        self.contrast_label = ctk.CTkLabel(self.sub_adjust, text=get_text("contrast_label"))
        self.contrast_label.pack(pady=(10, 0))
        self.contrast_slider = ctk.CTkSlider(self.sub_adjust, from_=0.5, to=3.0, command=self.update_filter_params)
        self.contrast_slider.set(1.0)
        self.contrast_slider.pack(pady=5, padx=10, fill="x")

        # Brightness
        self.brightness_label = ctk.CTkLabel(self.sub_adjust, text=get_text("brightness_label"))
        self.brightness_label.pack(pady=(10, 0))
        self.brightness_slider = ctk.CTkSlider(self.sub_adjust, from_=-100, to=100, command=self.update_filter_params)
        self.brightness_slider.set(0)
        self.brightness_slider.pack(pady=5, padx=10, fill="x")

        # Gamma
        self.gamma_label = ctk.CTkLabel(self.sub_adjust, text=get_text("gamma_label"))
        self.gamma_label.pack(pady=(10, 0))
        self.gamma_slider = ctk.CTkSlider(self.sub_adjust, from_=0.1, to=3.0, command=self.update_filter_params)
        self.gamma_slider.set(1.0)
        self.gamma_slider.pack(pady=5, padx=10, fill="x")

        # Edge Detection Switch
        self.edge_switch = ctk.CTkSwitch(self.sub_adjust, text=get_text("edge_switch"), command=self.update_filter_params)
        self.edge_switch.pack(pady=10, padx=10)

        # Invert Mask
        self.invert_switch = ctk.CTkSwitch(self.sub_adjust, text=get_text("invert_switch"), command=self.update_filter_params)
        self.invert_switch.pack(pady=20, padx=10)

        # --- SUBTAB NOISE ---
        # Blur
        self.blur_label = ctk.CTkLabel(self.sub_noise, text=get_text("blur_label"))
        self.blur_label.pack(pady=(10, 0))
        self.blur_slider = ctk.CTkSlider(self.sub_noise, from_=0, to=10, number_of_steps=10, command=self.update_filter_params)
        self.blur_slider.set(0)
        self.blur_slider.pack(pady=5, padx=10, fill="x")

        # Morphology
        self.filter_iter_label = ctk.CTkLabel(self.sub_noise, text=get_text("filter_iter_label"))
        self.filter_iter_label.pack(pady=(10, 0))
        self.filter_iter_slider = ctk.CTkSlider(self.sub_noise, from_=0, to=5, number_of_steps=5, command=self.update_filter_params)
        self.filter_iter_slider.set(1)
        self.filter_iter_slider.pack(pady=5, padx=10, fill="x")

        # Dilate
        self.dilate_label = ctk.CTkLabel(self.sub_noise, text=get_text("dilate_label"))
        self.dilate_label.pack(pady=(10, 0))
        self.dilate_slider = ctk.CTkSlider(self.sub_noise, from_=0, to=10, number_of_steps=10, command=self.update_filter_params)
        self.dilate_slider.set(0)
        self.dilate_slider.pack(pady=5, padx=10, fill="x")

        # Binary Mask Switch
        self.binary_mask_switch = ctk.CTkSwitch(self.sub_noise, text=get_text("binary_mask_switch"), command=self.update_filter_params)
        self.binary_mask_switch.pack(pady=15, padx=10)
        
        self.contour_filling_switch = ctk.CTkSwitch(self.sub_noise, text=get_text("contour_filling_switch"), command=self.update_filter_params)
        self.contour_filling_switch.pack(pady=15, padx=10)

        # Contour Color Button
        self.contour_color_btn = ctk.CTkButton(self.sub_noise, text=get_text("contour_color_btn"), command=self.choose_contour_color)
        self.contour_color_btn.pack(pady=10, padx=10)

        # Min Contour Area Slider
        self.min_area_label = ctk.CTkLabel(self.sub_noise, text=get_text("min_area_label"))
        self.min_area_label.pack(pady=(10, 0))
        self.min_area_slider = ctk.CTkSlider(self.sub_noise, from_=0, to=500, number_of_steps=100, command=self.update_filter_params)
        self.min_area_slider.set(20)
        self.min_area_slider.pack(pady=10, padx=10)

        # Intelligent Note Filter Switch
        self.intel_filter_switch = ctk.CTkSwitch(self.sub_noise, text=get_text("intel_filter_switch"), command=self.update_filter_params)
        self.intel_filter_switch.pack(pady=10, padx=10)

        # Bottom Buttons
        self.convert_btn = ctk.CTkButton(self.sidebar, text=get_text("start_btn"), command=self.start_conversion, fg_color="green", hover_color="darkgreen")
        self.convert_btn.pack(side="bottom", padx=20, pady=(10, 20), fill="x")
        
        self.settings_btn = ctk.CTkButton(self.sidebar, text="⚙️", command=self.show_settings, width=32, fg_color="transparent", border_width=1)
        self.settings_btn.pack(side="bottom", pady=5)

        # Main Preview Area
        self.preview_area = ctk.CTkFrame(self, corner_radius=10)
        self.preview_area.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.preview_area.grid_columnconfigure(0, weight=1)
        self.preview_area.grid_rowconfigure(1, weight=1) # Row 0 for toolbar, Row 1 for canvas

        # Toolbar Preview (Blender style)
        self.toolbar_preview = ctk.CTkFrame(self.preview_area, height=40, corner_radius=5)
        self.toolbar_preview.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 0))
        
        self.vp1_switch = ctk.CTkCheckBox(self.toolbar_preview, text=get_text("vp1_label"), command=self.update_preview)
        self.vp1_switch.select()
        self.vp1_switch.pack(side="left", padx=10)
        
        self.vp2_switch = ctk.CTkCheckBox(self.toolbar_preview, text=get_text("vp2_label"), command=self.update_preview)
        self.vp2_switch.deselect()
        self.vp2_switch.pack(side="left", padx=10)

        self.align_keys_btn = ctk.CTkButton(self.toolbar_preview, text=get_text("align_btn"), command=self.align_manual_keys, width=80, height=24)
        self.align_keys_btn.pack(side="right", padx=10)

        # 3. Canvas for Preview
        self.canvas = tk.Canvas(self.preview_area, bg="black", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 5))
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)

        self.dragging_key_idx = -1
        self.resizing_key_idx = -1
        self.selected_key_idx = -1
        self.drag_start_coords = None
        self.new_key_start = None
        
        # 4. Navigation Slider
        self.slider_frame = ctk.CTkFrame(self.preview_area, fg_color="transparent")
        self.slider_frame.grid(row=2, column=0, padx=20, pady=(0, 5), sticky="ew")
        
        self.video_slider = ctk.CTkSlider(self.slider_frame, from_=0, to=1, command=self.on_slider_change)
        self.video_slider.set(0)
        self.video_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.slider_label = ctk.CTkLabel(self.slider_frame, text="0 / 0", width=80)
        self.slider_label.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(self.preview_area)
        self.progress_bar.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self.preview_area, text=get_text("status_ready"))
        self.status_label.grid(row=4, column=0, padx=20, pady=(0, 10))

        # Version label in the corner of preview area
        self.v_label = ctk.CTkLabel(self.preview_area, text="v2.1.0", font=ctk.CTkFont(size=10), text_color="gray")
        self.v_label.place(relx=1.0, rely=1.0, x=-15, y=-15, anchor="se")

        # Set default target selector
        self.set_target_selector("start")

    def on_slider_change(self, value):
        if not self.processor or self.is_converting: return
        self.preview_frame_idx = int(value * self.processor.frame_count)
        if self.preview_frame_idx >= self.processor.frame_count:
            self.preview_frame_idx = self.processor.frame_count - 1
        
        # Aggiorna il testo dello slider
        self.slider_label.configure(text=f"{self.preview_frame_idx} / {self.processor.frame_count}")

        # Update the selected entry with current frame when moving the slider
        if not self.is_playing:
            if self.target_frame_selector == "start":
                self.start_frame_entry.delete(0, tk.END)
                self.start_frame_entry.insert(0, str(self.preview_frame_idx))
            else:
                self.end_frame_entry.delete(0, tk.END)
                self.end_frame_entry.insert(0, str(self.preview_frame_idx))
            # No need to call update_frame_indices here to avoid loops, 
            # but update the internal processor values
            try:
                if self.target_frame_selector == "start":
                    self.processor.start_frame = self.preview_frame_idx
                else:
                    self.processor.end_frame = self.preview_frame_idx
            except: pass
        
        # Se stiamo trascinando lo slider mentre il video è in pausa, aggiorniamo la preview
        if not self.is_playing:
            self.update_preview()

    def toggle_language(self):
        self.lang = "en-EN" if self.lang == "it-IT" else "it-IT"
        load_translations(self.lang)
        self.update_ui_text()

    def get_text_by_lang(self, key, lang):
        # Temp load to get specific text
        lang_file = get_resource_path(os.path.join("Localization", f"{lang}.json"))
        if os.path.exists(lang_file):
            try:
                with open(lang_file, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                return data.get(key, key)
            except: pass
        return key

    def update_ui_text(self):
        self.title(get_text("title"))
        # Tab titles (must be updated via tabview)
        for tab_key in ["tab_video", "tab_auto", "tab_manual", "tab_midi", "tab_filter"]:
            for btn_key in list(self.tabview._segmented_button._buttons_dict.keys()):
                if btn_key in [self.get_text_by_lang(tab_key, "it-IT"), self.get_text_by_lang(tab_key, "en-EN")]:
                    self.tabview._segmented_button._buttons_dict[btn_key].configure(text=get_text(tab_key))

        self.load_btn.configure(text=get_text("load_video"))
        self.height_slider_label.configure(text=get_text("height_label"))
        self.area_slider_label.configure(text=get_text("area_label"))
        self.threshold_slider_label.configure(text=get_text("threshold_label"))
        self.start_key_label.configure(text=get_text("start_key_label"))
        self.bpm_label.configure(text=get_text("bpm_label"))
        self.quantize_switch.configure(text=get_text("quantize_switch"))
        self.advanced_label.configure(text=get_text("sensitivity_label"))
        self.white_sens.configure(placeholder_text=get_text("white_placeholder"))
        self.black_sens.configure(placeholder_text=get_text("black_placeholder"))
        self.frames_label.configure(text=get_text("start_frame_label"))
        self.manual_switch.configure(text=get_text("manual_mode_switch"))
        self.manual_hint.configure(text=get_text("manual_mode_hint"))
        self.play_hint.configure(text=get_text("play_hint"))
        self.convert_btn.configure(text=get_text("start_btn"))
        
        self.filter_switch.configure(text=get_text("filter_switch"))
        self.hue_label.configure(text=get_text("hue_range"))
        self.sat_label.configure(text=get_text("sat_range"))
        self.val_label.configure(text=get_text("val_range"))
        self.filter_iter_label.configure(text=get_text("filter_iter_label"))
        self.note_names_switch.configure(text=get_text("note_names_switch"))
        
        # Update subtabs
        for sub_key in ["subtab_hsv", "subtab_adjust", "subtab_noise"]:
            for btn_key in list(self.filter_tabs._segmented_button._buttons_dict.keys()):
                if btn_key in [self.get_text_by_lang(sub_key, "it-IT"), self.get_text_by_lang(sub_key, "en-EN")]:
                    self.filter_tabs._segmented_button._buttons_dict[btn_key].configure(text=get_text(sub_key))
        
        self.contrast_label.configure(text=get_text("contrast_label"))
        self.brightness_label.configure(text=get_text("brightness_label"))
        self.gamma_label.configure(text=get_text("gamma_label"))
        self.blur_label.configure(text=get_text("blur_label"))
        self.invert_switch.configure(text=get_text("invert_switch"))
        self.edge_switch.configure(text=get_text("edge_switch"))
        self.dilate_label.configure(text=get_text("dilate_label"))
        self.binary_mask_switch.configure(text=get_text("binary_mask_switch"))
        self.contour_filling_switch.configure(text=get_text("contour_filling_switch"))
        self.contour_color_btn.configure(text=get_text("contour_color_btn"))
        self.min_area_label.configure(text=get_text("min_area_label"))
        self.intel_filter_switch.configure(text=get_text("intel_filter_switch"))
        
        # Toolbar labels
        self.vp1_switch.configure(text=get_text("vp1_label"))
        self.vp2_switch.configure(text=get_text("vp2_label"))
        self.align_keys_btn.configure(text=get_text("align_btn"))

        # Update Min/Max labels
        self.hue_min_label.configure(text=get_text("min_label"))
        self.hue_max_label.configure(text=get_text("max_label"))
        self.sat_min_label.configure(text=get_text("min_label"))
        self.sat_max_label.configure(text=get_text("max_label"))
        self.val_min_label.configure(text=get_text("min_label"))
        self.val_max_label.configure(text=get_text("max_label"))

        # Update dynamic labels for filter
        if self.processor:
            self.update_filter_params()
        
        # Update version label if language changed (though version is static, it's good practice)
        self.v_label.configure(text="v2.1.0")
        
        # Update settings window if open
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.show_settings() # Re-draw window content
        
        # Update status label with current text if it's one of the standard ones
        if self.processor:
            self.status_label.configure(text=get_text("status_loaded").format(os.path.basename(self.processor.video_path)))
        else:
            self.status_label.configure(text=get_text("status_ready"))

    def set_target_selector(self, target):
        self.target_frame_selector = target
        if target == "start":
            self.start_frame_entry.configure(border_color="green")
            self.end_frame_entry.configure(border_color=["#979da2", "#565b5e"])
            # Jump preview to start frame
            try:
                f = int(self.start_frame_entry.get())
                self.preview_frame_idx = f
                self.update_navigation_ui()
                self.update_preview()
            except: pass
        else:
            self.end_frame_entry.configure(border_color="green")
            self.start_frame_entry.configure(border_color=["#979da2", "#565b5e"])
            # Jump preview to end frame
            try:
                f = int(self.end_frame_entry.get())
                self.preview_frame_idx = f
                self.update_navigation_ui()
                self.update_preview()
            except: pass

    def toggle_play(self):
        if not self.processor: return
        if self.is_playing:
            self.is_playing = False
            self.play_btn.configure(text="▶")
            # Update the selected entry with current frame
            if self.target_frame_selector == "start":
                self.start_frame_entry.delete(0, tk.END)
                self.start_frame_entry.insert(0, str(self.preview_frame_idx))
            else:
                self.end_frame_entry.delete(0, tk.END)
                self.end_frame_entry.insert(0, str(self.preview_frame_idx))
            self.update_frame_indices()
        else:
            self.is_playing = True
            self.play_btn.configure(text="⏸")
            if not self.play_thread or not self.play_thread.is_alive():
                self.play_thread = threading.Thread(target=self.play_video_loop, daemon=True)
                self.play_thread.start()

    def play_video_loop(self):
        while self.is_playing and self.processor:
            self.preview_frame_idx += 1
            if self.preview_frame_idx >= self.processor.frame_count:
                self.preview_frame_idx = 0
            
            # Update slider and label
            self.after(0, self.update_navigation_ui)
            
            # Use after to update UI from thread
            self.after(0, self.update_preview)
            time.sleep(1/self.processor.fps)

    def update_navigation_ui(self):
        if not self.processor: return
        # Update slider value without triggering command
        val = self.preview_frame_idx / self.processor.frame_count
        self.video_slider.set(val)
        self.slider_label.configure(text=f"{self.preview_frame_idx} / {self.processor.frame_count}")

        self.bind("<KeyPress>", self.handle_keypress)
        
    def handle_keypress(self, event):
        if not self.processor: return
        
        # Determine if SHIFT is pressed
        shift = (event.state & 0x1) != 0
        # Determine if CTRL is pressed
        ctrl = (event.state & 0x4) != 0
        
        # 1. Preview Frame Navigation
        if not ctrl: # Only if CTRL is NOT pressed (to not conflict with manual keys)
            if event.keysym == "comma": # , (frame -1)
                self.change_preview_frame(-1)
            elif event.keysym == "period": # . (frame +1)
                self.change_preview_frame(1)
            elif event.keysym == "Left":
                if shift:
                    self.change_preview_frame(-10)
                else:
                    self.change_preview_frame(-1)
            elif event.keysym == "Right":
                if shift:
                    self.change_preview_frame(10)
                else:
                    self.change_preview_frame(1)

        # 2. Manual Keys Movement (CTRL + Arrows)
        if ctrl and self.processor.use_manual_mode:
            step = 1
            dx, dy = 0, 0
            if event.keysym == "Left": dx = -step
            elif event.keysym == "Right": dx = step
            elif event.keysym == "Up": dy = -step
            elif event.keysym == "Down": dy = step
            
            if dx != 0 or dy != 0:
                # Se abbiamo una chiave selezionata, sposta solo quella.
                if hasattr(self, 'selected_key_idx') and self.selected_key_idx != -1:
                    idx = self.selected_key_idx
                    if 0 <= idx < len(self.processor.manual_keys):
                        self.processor.manual_keys[idx]['x'] += dx
                        self.processor.manual_keys[idx]['y'] += dy
                else:
                    # Altrimenti sposta tutte le chiavi (fallback)
                    for key in self.processor.manual_keys:
                        key['x'] += dx
                        key['y'] += dy
                self.update_preview()

    def change_preview_frame(self, delta):
        if not self.processor: return
        new_idx = self.preview_frame_idx + delta
        if 0 <= new_idx < self.processor.frame_count:
            self.preview_frame_idx = new_idx
            self.update_navigation_ui()
            self.update_preview()

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")])
        if path:
            self.processor = VideoProcessor(path)
            self.start_frame_entry.delete(0, tk.END)
            self.start_frame_entry.insert(0, "0")
            self.end_frame_entry.delete(0, tk.END)
            self.end_frame_entry.insert(0, str(self.processor.frame_count))
            self.status_label.configure(text=get_text("status_loaded").format(os.path.basename(path)))
            self.update_navigation_ui()
            self.update_preview()

    def update_frame_indices(self):
        if not self.processor: return
        try:
            start_f = int(self.start_frame_entry.get())
            end_f = int(self.end_frame_entry.get())
            
            # Validation
            if start_f < 0: start_f = 0
            if start_f >= self.processor.frame_count: start_f = self.processor.frame_count - 1
            if end_f <= start_f: end_f = start_f + 1
            if end_f > self.processor.frame_count: end_f = self.processor.frame_count
            
            self.processor.start_frame = start_f
            self.processor.end_frame = end_f
            self.preview_frame_idx = start_f
            
            # Update entries in case they were corrected
            self.start_frame_entry.delete(0, tk.END)
            self.start_frame_entry.insert(0, str(start_f))
            self.end_frame_entry.delete(0, tk.END)
            self.end_frame_entry.insert(0, str(end_f))
            
            # Sync slider position
            self.update_navigation_ui()
            
            self.update_preview()
        except ValueError:
            pass

    def update_filter_params(self, value=None):
        if not self.processor: return
        self.processor.use_color_filter = self.filter_switch.get() == 1
        
        # Range values HSV
        h_min, h_max = int(self.hue_min_slider.get()), int(self.hue_max_slider.get())
        s_min, s_max = int(self.sat_min_slider.get()), int(self.sat_max_slider.get())
        v_min, v_max = int(self.val_min_slider.get()), int(self.val_max_slider.get())
        
        self.processor.hsv_min = np.array([h_min, s_min, v_min])
        self.processor.hsv_max = np.array([h_max, s_max, v_max])
        
        # New adjustments
        self.processor.contrast = float(self.contrast_slider.get())
        self.processor.brightness = float(self.brightness_slider.get())
        self.processor.gamma = float(self.gamma_slider.get())
        self.processor.edge_detection = self.edge_switch.get() == 1
        self.processor.invert_mask = self.invert_switch.get() == 1
        self.processor.blur_size = int(self.blur_slider.get())
        self.processor.filter_iterations = int(self.filter_iter_slider.get())
        self.processor.dilate_iterations = int(self.dilate_slider.get())
        self.processor.show_binary_mask = self.binary_mask_switch.get() == 1
        self.processor.use_contour_filling = self.contour_filling_switch.get() == 1
        self.processor.min_contour_area = int(self.min_area_slider.get())
        self.processor.use_intelligent_filter = self.intel_filter_switch.get() == 1
        
        # Update labels with current values
        self.hue_label.configure(text=f"{get_text('hue_range')} (Min: {h_min}, Max: {h_max})")
        self.sat_label.configure(text=f"{get_text('sat_range')} (Min: {s_min}, Max: {s_max})")
        self.val_label.configure(text=f"{get_text('val_range')} (Min: {v_min}, Max: {v_max})")
        
        self.contrast_label.configure(text=f"{get_text('contrast_label')} ({self.processor.contrast:.1f})")
        self.brightness_label.configure(text=f"{get_text('brightness_label')} ({int(self.processor.brightness)})")
        self.gamma_label.configure(text=f"{get_text('gamma_label')} ({self.processor.gamma:.1f})")
        self.blur_label.configure(text=f"{get_text('blur_label')} ({self.processor.blur_size})")
        self.filter_iter_label.configure(text=f"{get_text('filter_iter_label')} ({self.processor.filter_iterations})")
        self.dilate_label.configure(text=f"{get_text('dilate_label')} ({self.processor.dilate_iterations})")
        self.min_area_label.configure(text=f"{get_text('min_area_label')} ({self.processor.min_contour_area})")
        
        # Force a fresh frame read to apply new filter settings
        if not self.is_playing and not self.is_converting:
            self.update_preview()

    def choose_contour_color(self):
        if not self.processor: return
        # Convert BGR to Hex
        current_color = "#{:02x}{:02x}{:02x}".format(self.processor.contour_color[2], self.processor.contour_color[1], self.processor.contour_color[0])
        color_code = colorchooser.askcolor(title=get_text("choose_color_title"), initialcolor=current_color)
        if color_code[0]:
            # Convert RGB (from colorchooser) to BGR (for OpenCV)
            rgb = color_code[0]
            self.processor.contour_color = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
            self.update_filter_params()

    def toggle_note_names(self):
        if not self.processor: return
        self.processor.show_note_names = self.note_names_switch.get() == 1
        self.update_preview()

    def toggle_manual_mode(self):
        if not self.processor: return
        self.processor.use_manual_mode = self.manual_switch.get() == 1
        # In this version with tabs, we don't need to hide sliders manually 
        # as they are in different tabs.
        self.update_preview()

    def get_video_coords(self, canvas_x, canvas_y):
        if not self.processor: return None
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10: return None

        # Calculate original w, h based on viewports
        show_v1 = self.vp1_switch.get() == 1
        show_v2 = self.vp2_switch.get() == 1
        v_num = (1 if show_v1 != show_v2 else 2) if (show_v1 or show_v2) else 1
        
        orig_h, orig_w = self.processor.height, self.processor.width
        w_total = orig_w * v_num
        h_total = orig_h
        
        ratio = min(cw/w_total, ch/h_total)
        new_w, new_h = int(w_total*ratio), int(h_total*ratio)
        
        # Offset to center
        ox = (cw - new_w) // 2
        oy = (ch - new_h) // 2
        
        vx_total = int((canvas_x - ox) / ratio)
        vy = int((canvas_y - oy) / ratio)
        
        # Map vx_total to viewport 0 (local vx)
        vx = vx_total % orig_w
        
        if 0 <= vx_total < w_total and 0 <= vy < h_total:
            return vx, vy
        return None

    def on_canvas_click(self, event):
        if not self.processor or not self.processor.use_manual_mode: return
        coords = self.get_video_coords(event.x, event.y)
        if not coords: return
        vx, vy = coords
        
        # Check if clicking a handle for resizing or inside a box for dragging
        self.dragging_key_idx = -1
        self.resizing_key_idx = -1
        self.selected_key_idx = -1
        self.drag_start_coords = (vx, vy)
        
        for i, key in enumerate(self.processor.manual_keys):
            x, y, w, h = key['x'], key['y'], key['w'], key['h']
            # Resize handle (bottom-right corner)
            if abs(vx - (x + w)) < 15 and abs(vy - (y + h)) < 15:
                self.resizing_key_idx = i
                self.selected_key_idx = i
                self.update_preview()
                return
            # Drag area
            if x <= vx <= x + w and y <= vy <= y + h:
                self.dragging_key_idx = i
                self.selected_key_idx = i
                self.drag_offset = (vx - x, vy - y)
                self.update_preview()
                return
        
        # If not clicking any box, prepare to create a new one
        self.new_key_start = (vx, vy)
        self.update_preview()

    def on_canvas_drag(self, event):
        if not self.processor or not self.processor.use_manual_mode: return
        coords = self.get_video_coords(event.x, event.y)
        if not coords: return
        vx, vy = coords
        
        if self.resizing_key_idx != -1:
            key = self.processor.manual_keys[self.resizing_key_idx]
            key['w'] = max(5, vx - key['x'])
            key['h'] = max(5, vy - key['y'])
            self.update_preview()
        elif self.dragging_key_idx != -1:
            key = self.processor.manual_keys[self.dragging_key_idx]
            key['x'] = vx - self.drag_offset[0]
            key['y'] = vy - self.drag_offset[1]
            self.update_preview()

    def on_canvas_release(self, event):
        if not self.processor or not self.processor.use_manual_mode: return
        
        if self.new_key_start:
            coords = self.get_video_coords(event.x, event.y)
            if coords:
                vx, vy = coords
                x1, y1 = self.new_key_start
                x, y = min(x1, vx), min(y1, vy)
                w, h = abs(vx - x1), abs(vy - y1)
                
                if w > 5 and h > 5:
                    self.processor.manual_keys.append({
                        'x': x, 'y': y, 'w': w, 'h': h, 'type': 'manual'
                    })
                    # Seleziona la nuova chiave appena creata
                    self.selected_key_idx = len(self.processor.manual_keys) - 1
            
            self.new_key_start = None
            self.update_preview()
        
        self.dragging_key_idx = -1
        self.resizing_key_idx = -1

    def on_canvas_right_click(self, event):
        if not self.processor or not self.processor.use_manual_mode: return
        coords = self.get_video_coords(event.x, event.y)
        if not coords: return
        vx, vy = coords
        
        # Remove box if right-clicking inside
        to_remove = -1
        for i, key in enumerate(self.processor.manual_keys):
            if key['x'] <= vx <= key['x'] + key['w'] and key['y'] <= vy <= key['y'] + key['h']:
                to_remove = i
                break
        
        if to_remove != -1:
            self.processor.manual_keys.pop(to_remove)
            self.selected_key_idx = -1
            self.update_preview()

    def update_height(self, value):
        if self.processor:
            self.processor.keyboard_y = float(value)
            self.update_preview()

    def update_threshold(self, value):
        if self.processor:
            self.processor.threshold = float(value)
            self.update_preview()

    def update_detection_height(self, value):
        if self.processor:
            self.processor.detection_height = int(value)
            self.update_preview()

    def update_preview(self, force_frame=None):
        if not self.processor: return
        
        # Determine viewports to show
        show_v1 = self.vp1_switch.get() == 1
        show_v2 = self.vp2_switch.get() == 1
        
        if not show_v1 and not show_v2:
            self.canvas.delete("all")
            return

        # 1. Get Frames
        self.processor.cap.set(cv2.CAP_PROP_POS_FRAMES, self.preview_frame_idx)
        ret, frame_orig = self.processor.cap.read()
        if not ret: return
        
        frame_filtered = self.processor.apply_color_filter(frame_orig.copy())

        # 2. Combine Viewports
        if show_v1 and show_v2:
            h, w = frame_orig.shape[:2]
            combined = np.zeros((h, w*2, 3), dtype=np.uint8)
            combined[:, :w] = frame_orig
            combined[:, w:] = frame_filtered
            final_frame = combined
            v_num = 2
        elif show_v1:
            final_frame = frame_orig
            v_num = 1
        else:
            final_frame = frame_filtered
            v_num = 1

        # 3. Draw Overlays
        self.draw_overlays(final_frame, v_num)

        # 4. Display in Canvas
        self.show_image(final_frame)
        self.last_preview_frame = final_frame

    def draw_overlays(self, frame, v_num):
        h, w_total = frame.shape[:2]
        w = w_total // v_num
        
        for v in range(v_num):
            offset_x = v * w
            
            if self.processor.use_manual_mode:
                for i, key in enumerate(self.processor.manual_keys):
                    kx, ky, kw, kh = key['x'], key['y'], key['w'], key['h']
                    # Color highlighting for selected key
                    color = (255, 0, 0) if i == self.selected_key_idx else (0, 255, 255) # Red if selected, Yellow otherwise
                    cv2.rectangle(frame, (offset_x + kx, ky), (offset_x + kx + kw, ky + kh), color, 2)
                    cv2.circle(frame, (offset_x + kx + kw, ky + kh), 4, color, -1)
                    midi_note = self.processor.start_key + i
                    text_label = self.processor.midi_to_note_name(midi_note) if self.processor.show_note_names else str(midi_note)
                    cv2.putText(frame, text_label, (offset_x + kx + 2, ky + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            else:
                y_px = int(h * self.processor.keyboard_y)
                h_half = self.processor.detection_height // 2
                cv2.rectangle(frame, (offset_x, y_px - h_half), (offset_x + w, y_px + h_half), (0, 255, 0), 2)
                
                # Draw key indicators if available
                if hasattr(self.processor, 'key_positions'):
                    c4_idx = self.processor.get_c4_index()
                    for i, kp in enumerate(self.processor.key_positions):
                        kx = int(offset_x + kp['pos'])
                        ky = y_px
                        
                        # Use last detected state if possible, or just markers
                        color = (255, 255, 255) if kp['type'] == 'white' else (60, 60, 60)
                        if i == c4_idx:
                            cv2.circle(frame, (kx, ky), 8, (0, 0, 255), -1)
                            cv2.putText(frame, "C4", (kx - 10, ky - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        cv2.circle(frame, (kx, ky), 5, color, -1)

    def align_manual_keys(self):
        if not self.processor or not self.processor.manual_keys: return
        # Align all keys to the same Y and Height of the first one
        ref_y = self.processor.manual_keys[0]['y']
        ref_h = self.processor.manual_keys[0]['h']
        self.processor.manual_keys.sort(key=lambda k: k['x'])
        for key in self.processor.manual_keys:
            key['y'] = ref_y
            key['h'] = ref_h
        self.update_preview()
        self.status_label.configure(text=get_text("status_aligned"))

    def show_image(self, cv_img):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10: return

        # Resize maintaining aspect ratio
        h, w = cv_img.shape[:2]
        ratio = min(cw/w, ch/h)
        new_w, new_h = int(w*ratio), int(h*ratio)
        
        cv_img = cv2.resize(cv_img, (new_w, new_h))
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        
        img = Image.fromarray(cv_img)
        self.tk_img = ImageTk.PhotoImage(image=img)
        
        self.canvas.delete("all")
        self.canvas.create_image(cw//2, ch//2, image=self.tk_img, anchor="center")

    def on_canvas_resize(self, event):
        self.update_preview()

    def start_conversion(self):
        if not self.processor:
            messagebox.showwarning(get_text("msg_attention"), get_text("error_video"))
            return

        if self.is_converting:
            self.stop_conversion()
            return

        output_path = filedialog.asksaveasfilename(defaultextension=".mid", filetypes=[("MIDI files", "*.mid")])
        if not output_path: return
        
        try:
            self.processor.start_frame = int(self.start_frame_entry.get())
            self.processor.end_frame = int(self.end_frame_entry.get())
            self.processor.start_key = int(self.start_key_entry.get())
            self.processor.bpm = int(self.bpm_entry.get())
            self.processor.use_quantization = self.quantize_switch.get() == 1
            self.processor.quantization_value = self.quantize_value.get()
            self.processor.white_threshold_factor = float(self.white_sens.get())
            self.processor.black_threshold_factor = float(self.black_sens.get())
            self.processor.use_manual_mode = self.manual_switch.get() == 1
            
            # Recalibrate on start frame before conversion
            frame = self.processor.get_frame(self.processor.start_frame)
            if frame is not None:
                self.processor.analyze_keyboard(frame)
        except:
            messagebox.showerror(get_text("msg_error"), get_text("error_params"))
            return

        self.convert_btn.configure(text=get_text("stop_btn"), fg_color="red", hover_color="darkred")
        self.is_converting = True
        self.stop_event.clear()
        
        def run():
            try:
                logging.info(f"Avvio conversione per: {self.processor.video_path}")
                success = self.processor.convert_to_midi(output_path, 
                                                       progress_callback=self.update_progress,
                                                       status_callback=self.update_status_label,
                                                       frame_callback=self.update_runtime_preview,
                                                       stop_event=self.stop_event)
                logging.info(f"Conversione terminata. Successo: {success}")
                self.after(0, lambda: self.on_conversion_finished(success))
            except Exception as e:
                logging.error(f"Errore durante la conversione: {e}", exc_info=True)
                self.after(0, lambda: self.on_conversion_finished(False))

        threading.Thread(target=run, daemon=True).start()

    def update_progress(self, value):
        self.after(0, lambda: self.progress_bar.set(value))

    def update_status_label(self, count, total):
        text = get_text("status_processing").format(count, total)
        self.after(0, lambda: self.status_label.configure(text=text))

    def update_runtime_preview(self, frame):
        # Apply filter if active during conversion
        if self.processor and self.processor.use_color_filter:
            frame = self.processor.apply_color_filter(frame)
        self.last_preview_frame = frame
        self.after(0, lambda: self.show_image(frame))

    def stop_conversion(self):
        if self.is_converting:
            self.stop_event.set()
            self.convert_btn.configure(state="disabled")

    def on_conversion_finished(self, success):
        self.is_converting = False
        self.convert_btn.configure(state="normal", text=get_text("start_btn"), fg_color="green", hover_color="darkgreen")
        if success:
            messagebox.showinfo(get_text("msg_success"), get_text("conversion_success"))
        else:
            messagebox.showwarning(get_text("msg_interrupted"), get_text("conversion_interrupted"))

    def show_settings(self):
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.lift()
            # Clear window and redraw
            for widget in self.settings_window.winfo_children():
                widget.destroy()
        else:
            self.settings_window = ctk.CTkToplevel(self)
            self.settings_window.title(get_text("settings_title"))
            self.settings_window.geometry("500x500")
            self.settings_window.after(100, self.settings_window.lift)
            self.settings_window.attributes("-topmost", True)
        
        # Title
        label_title = ctk.CTkLabel(self.settings_window, text=get_text("title"), font=ctk.CTkFont(size=18, weight="bold"))
        label_title.pack(pady=(20, 10))
        
        # Credits Text (removed from here, moved to a dedicated popup)
        # label_text = ctk.CTkLabel(self.settings_window, text=get_text("credits_text"), justify="center")
        # label_text.pack(pady=10, padx=20)

        # Language Toggle
        lang_frame = ctk.CTkFrame(self.settings_window, fg_color="transparent")
        lang_frame.pack(pady=20)
        
        lang_label = ctk.CTkLabel(lang_frame, text=get_text("select_lang"))
        lang_label.pack(side="left", padx=10)
        
        lang_btn = ctk.CTkButton(lang_frame, text=get_text("lang_btn"), command=self.toggle_language)
        lang_btn.pack(side="right", padx=10)

        # Credits Button in settings (duplicate of the one in sidebar but for consistency)
        credits_btn = ctk.CTkButton(self.settings_window, text=get_text("credits_btn"), command=self.show_credits)
        credits_btn.pack(pady=5)
        
        # Close Button
        close_btn = ctk.CTkButton(self.settings_window, text=get_text("close_btn"), command=self.settings_window.destroy)
        close_btn.pack(pady=20)

    def show_credits(self):
        messagebox.showinfo(get_text("credits_title"), get_text("credits_text"))

if __name__ == "__main__":
    app = ModernApp()
    app.mainloop()
