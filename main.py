# VideoToMidiConverter
# Copyright (C) 2024-2025 venividiviciuss
#
# This project is an advanced tool for converting videos of musical keyboards into MIDI files.
# It has been developed with passion and dedication by venividiviciuss.
#
# Thanks to everyone who has supported this project.
# If you would like to contribute to the project or suggest improvements:
# please visit the GitHub repository: [https://github.com/venividiviciuss/Video-To-Midi-Converter]
#
# All rights reserved.

import cv2
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, font
import os
from PIL import Image, ImageTk
import numpy as np
from mido import Message, MetaMessage, MidiFile, MidiTrack
import threading
import sys
import pygame

# Classe di configurazione comune
class Com:
    def __init__(self):
        self.video_path = "./video/video.mp4"
        self.output_path = "./midi/output.mid"
        self.keyboard_height = 0.75
        self.threshold = 30
        self.start_key = 1
        self.end_key = 88
        self.start_frame = 0.0
        self.end_frame = -1.0

        self.preview_image = "./start_frame.jpg"

        self.white_threshold = None
        self.black_threshold = None
        self.key_positions = []
        self.default_values = []
        self.middle_c = 40
        self.key_width = 2

# Classe interfaccia utente
class Gui:
    def __init__(self, root):
        self.root = root
        self.root.iconbitmap("./favicon/midi.ico")
        self.root.title("Video to MIDI Converter")
        self.root.geometry("600x430")
        self.root.resizable(False, False)
        self.root.overrideredirect(True)

        # Variabili per il trascinamento
        self.dragging = False
        self.prev_x = 0
        self.prev_y = 0

        self.process_stop_callback = threading.Event()
        self.preview_stop_callback = threading.Event()

        self.converter = VideoToMidiConverter(self.process_stop_callback, status_callback=self.update_status, progress_callback=self.update_progress)
        self.preview = Preview(self, self.preview_stop_callback, status_callback=self.update_status)

        self.root.bind("<Configure>", self.on_main_window_move)
        self.current_main_x = self.root.winfo_x()
        self.current_main_y = self.root.winfo_y()


        self.initialize_variables()
        self.create_widgets()
        self.style_gui()
        self.play_music()
        
        # Bind per il trascinamento della finestra
        self.title_frame.bind("<ButtonPress-1>", self.start_drag)
        self.title_frame.bind("<B1-Motion>", self.do_drag)

    def style_gui(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Configurazione degli stili
        root.configure(bg="#1f2020")
        style.configure("TFrame", background="#1f2020") #1f2020 #3c3c3c
        style.configure("TLabel", background="#3c3c3c", foreground="white")
        style.configure("TScale", background="#3c3c3c", troughcolor="#f00") 
        style.configure("TButton", background="#007BFF", foreground="white")
        style.map("TButton", background=[("active", "#0056b3")])

        # Bind per il passaggio del mouse
        # self.minimize_button.bind("<Enter>", lambda e: self.minimize_button.config(bg="#ccc", activeforeground="white"))
        # self.minimize_button.bind("<Leave>", lambda e: self.minimize_button.config(bg="#1f2020", activeforeground="white"))      
        # self.maximize_button.bind("<Enter>", lambda e: self.maximize_button.config(bg="#ccc", activeforeground="white"))
        # self.maximize_button.bind("<Leave>", lambda e: self.maximize_button.config(bg="#1f2020", activeforeground="white"))
        self.close_button.bind("<Enter>", lambda e: self.close_button.config(bg="red", activeforeground="white"))
        self.close_button.bind("<Leave>", lambda e: self.close_button.config(bg="#1f2020", activeforeground="white"))

    def minimize_window(self):
        self.root.iconify()

    def toggle_maximize(self):
        if not self.maximized:
            self.root.state("zoomed")
        else:
            self.root.state("normal")
        self.maximized = not self.maximized

    def close_window(self):
            root.destroy()

    def start_drag(self, event):
        self.dragging = True
        self.prev_x = event.x
        self.prev_y = event.y

    def do_drag(self, event):
        if self.dragging:
            x = self.root.winfo_x() + event.x - self.prev_x
            y = self.root.winfo_y() + event.y - self.prev_y
            self.root.geometry(f"+{x}+{y}")

    def stop_drag(self, event):
        self.dragging = False

    def create_widgets(self):
        # Configura la griglia principale per espansione
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=0)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)

        self.title_frame = ttk.Frame(self.root)
        self.title_frame.grid(row=0 ,sticky=(tk.W, tk.E), padx=5, pady=5)

        self.title_frame.grid_columnconfigure(0, weight=0)
        self.title_frame.grid_columnconfigure(1, weight=1)
        self.title_frame.grid_columnconfigure(2, weight=100)

        # Icona
        self.icon_image = tk.PhotoImage(file="./favicon/midi16.png")
        self.icon_label = tk.Label(self.title_frame, image=self.icon_image, bg="#1f2020")
        self.icon_label.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W))

        # Titolo alla barra
        self.title_label = tk.Label(self.title_frame, text="Video to MIDI Converter", bg="#1f2020", fg="white")
        self.title_label.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.W))

        # Pulsante per ridurre a icona la finestra
        self.minimize_button = tk.Button(self.title_frame, text="_", state="disabled", command=self.minimize_window, width=3, bg="#1f2020", activebackground="#ccc", fg="white", bd=0)
        self.minimize_button.grid(row=0, column=2, sticky=(tk.N, tk.S, tk.E), padx=3)

        # Pulsante per massimizzare o ridurre la finestra
        self.maximize_button = tk.Button(self.title_frame, text="□", state="disabled", command=self.toggle_maximize, width=3, bg="#1f2020", activebackground="#ccc", fg="white", bd=0)
        self.maximize_button.grid(row=0, column=3, sticky=(tk.N, tk.S, tk.E), padx=3)

        # Pulsante per chiudere la finestra
        self.close_button = tk.Button(self.title_frame, text="X", command=self.close_window, width=3, bg="#1f2020", activebackground="red", fg="white", bd=0)
        self.close_button.grid(row=0, column=4, sticky=(tk.N, tk.S, tk.E), padx=3)

        # Frame principale
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=1, sticky=(tk.N, tk.S, tk.W, tk.E))

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=0)
        self.main_frame.rowconfigure(1, weight=0)
        self.main_frame.rowconfigure(2, weight=1)

        # # Frame per impostazioni video
        self.dir_frame = tk.Frame(self.main_frame, bg="#3c3c3c")
        self.dir_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.title_dir_frame = ttk.Label(self.dir_frame, text="Video and MIDI Settings")
        self.title_dir_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Configurazione della griglia del frame delle opzioni per l'espansione
        self.dir_frame.columnconfigure(0, weight=1)
        self.dir_frame.columnconfigure(1, weight=1)
        self.dir_frame.columnconfigure(2, weight=1)

        # Video input | MIDI output
        self.video_path_entry = self.create_label_entry(self.dir_frame, "Video URL o File:", "./video/video.mp4", 1, self.browse_video, self.video_path, str)
        self.output_path_entry = self.create_label_entry(self.dir_frame, "Output MIDI (.mid):", "./midi/output.mid", 2, self.browse_midi, self.output_path, str)

        # Frame per opzioni
        self.option_frame = tk.Frame(self.main_frame, bg="#3c3c3c")
        self.option_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.title_option_frame = ttk.Label(self.option_frame, text="Settings")
        self.title_option_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Configurazione della griglia del frame delle opzioni per l'espansione
        self.option_frame.columnconfigure(0, weight=1)
        self.option_frame.columnconfigure(1, weight=1)
        self.option_frame.columnconfigure(2, weight=1)

        # Altezza tastiera
        self.keyboard_height_entry = self.create_entry_with_label(self.option_frame, "Slider", "Keyboard Height (0-1):", "0.75", 1, 0, self.keyboard_height, (0, 1), float)
        
        # Tasto di inizio | Tasto di fine | Soglia attivazione
        self.start_key_entry = self.create_entry_with_label(self.option_frame, "Box", "Initial Key:", "1", 2, 0, self.start_key, None, int)
        self.end_key_entry = self.create_entry_with_label(self.option_frame, "Box", "Final Key:", "88", 2, 2, self.end_key, None, int)
        self.threshold_entry = self.create_entry_with_label(self.option_frame, "Box", "Threshold:", "30", 2, 4, self.threshold, None, int)
        
        # Inizio Frame | Fine Frame
        self.start_frame_entry = self.create_entry_with_label(self.option_frame, "Box", "Start Frame (s):", "0.0", 3, 0, self.start_frame, None, float)
        self.end_frame_entry = self.create_entry_with_label(self.option_frame, "Box", "End Frame (s):", "-1.0", 3, 2, self.end_frame, None, float)

        self.converse_frame = tk.Frame(self.main_frame, bg="#3c3c3c")
        self.converse_frame.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=5, pady=5)

        # Configura la colonna per l'espansione nel frame dei pulsanti
        self.converse_frame.columnconfigure(0, weight=100)
        self.converse_frame.columnconfigure(1, weight=0)
        self.converse_frame.columnconfigure(2, weight=0)
        self.converse_frame.columnconfigure(3, weight=1)
        self.converse_frame.columnconfigure(4, weight=0)
        self.converse_frame.rowconfigure(3, weight=1)

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.converse_frame, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Console log
        self.info_label = tk.Label(self.converse_frame, text="", justify="left", font=("Verdana", 8, "bold"), bg="lightgrey", anchor="w")
        self.info_label.grid(row=1, column=0, rowspan=3, sticky=(tk.N, tk.S, tk.W, tk.E), padx=5, pady=5)

        # Buttons
        self.convert_button = ttk.Button(self.converse_frame, text="Start Conversion", command=self.toggle_conversion)
        self.convert_button.grid(row=0, column=2, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.preview_button = ttk.Button(self.converse_frame, text="Preview", command=self.preview.image_preview)
        self.preview_button.grid(row=1, column=2, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.credits_button = tk.Button(self.converse_frame, image=self.info_photo, width=20, borderwidth=0, bg="#3c3c3c", activebackground="#3c3c3c")
        self.credits_button.grid(row=2, column=3, sticky=tk.E, padx=5, pady=5)

        self.music_button = tk.Button(self.converse_frame, image=self.play_photo, width=20, borderwidth=0, bg="#3c3c3c", activebackground="#3c3c3c", command=self.toggle_music)
        self.music_button.grid(row=2, column=4, sticky=tk.E, padx=5, pady=5)

    def create_label_entry(self, parent, label_text, default_value, row, command, var, v_type):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        entry = ttk.Entry(parent, width=50, textvariable=var)
        entry.grid(row=row, column=1, padx=5, pady=5)
        entry.bind("<FocusOut>", lambda event, v=var, d=default_value: self.check_empty_and_set_default(v, d, v_type))
        button = ttk.Button(parent, text="Browse", command=command)
        button.grid(row=row, column=2, padx=5, pady=5)
        return entry

    def create_entry_with_label(self, parent, type, label_text, default_value, row, col, var, value=(0, 100), v_type=None):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=col, sticky=tk.W, padx=5, pady=5)
        if type == "Box":
            entry = ttk.Entry(parent, width=10, textvariable=var)
            entry.grid(row=row, column=col+1, padx=5, pady=5)
            entry.bind("<FocusOut>", lambda event, v=var, d=default_value: self.check_empty_and_set_default(v, d, v_type))
            return entry
        elif type == "Slider":

            slider = ttk.Scale(parent, from_=value[0], to=value[1], orient=tk.HORIZONTAL, variable=var, style="TScale")
            slider.grid(row=row, column=col + 1, columnspan=4, padx=5, pady=5, sticky=tk.W+tk.E)
            slider_label = ttk.Label(parent, text=f"{round(float(default_value), 2)}")
            slider_label.grid(row=row, column=col+5, sticky=tk.E, padx= 5, pady=5)

            parent.columnconfigure(col+1, weight=4)
            parent.columnconfigure(col+5, weight=1)

            def update_slider_label(value):
                slider_label.config(text=str(round(float(value), 2)))

            slider.bind("<Motion>", lambda event: update_slider_label(slider.get()))

            return slider
        
    def initialize_variables(self):
        pygame.mixer.init()
        pygame.mixer.music.load("ab_ovo.wav")
        self.music_playing = False
        self.play_img = Image.open("./favicon/play.png")
        self.stop_img = Image.open("./favicon/stop.png")
        self.info_img = Image.open("./favicon/info.png")
        self.play_photo = ImageTk.PhotoImage(self.play_img)
        self.stop_photo = ImageTk.PhotoImage(self.stop_img)
        self.info_photo = ImageTk.PhotoImage(self.info_img)

        self.video_path = tk.StringVar(value="./video/video.mp4")
        self.output_path = tk.StringVar(value="./midi/output.mid")
        self.keyboard_height = tk.StringVar(value="0.75")
        self.threshold = tk.StringVar(value="30")
        self.start_key = tk.StringVar(value="1")
        self.end_key = tk.StringVar(value="88")
        self.start_frame = tk.StringVar(value="0.0")
        self.end_frame = tk.StringVar(value="-1.0")

        self.video_path.trace_add("write", lambda *args: self.update_trace("video_path", self.video_path, "./video/video.mp4", str))
        self.output_path.trace_add("write", lambda *args: self.update_trace("output_path", self.output_path, "./midi/output.mid", str))
        self.keyboard_height.trace_add("write", lambda *args: self.update_trace("keyboard_height", self.keyboard_height, 0.75, float))
        self.threshold.trace_add("write", lambda *args: self.update_trace("threshold", self.threshold, 30, int))
        self.start_key.trace_add("write", lambda *args: self.update_trace("start_key", self.start_key, 1, int))
        self.end_key.trace_add("write", lambda *args: self.update_trace("end_key", self.end_key, 88, int))
        self.start_frame.trace_add("write", lambda *args: self.update_trace("start_frame", self.start_frame, 0.0, float))
        self.end_frame.trace_add("write", lambda *args: self.update_trace("end_frame", self.end_frame, -1.0, float))
    
    def update_trace(self, com_w, gui_w, default_value=None, v_type=None):
            """Aggiorna le variabili comuni in base ai valori inseriti dall'utente nella gui"""
            input_value = gui_w.get()
            if input_value:
                try:
                    if v_type == int:
                        setattr(com, com_w, v_type(input_value))
                    elif v_type == float:
                        setattr(com, com_w, round(v_type(input_value), 2))
                    else:
                        setattr(com, com_w, input_value)
                    # print(f"{com_w}: {getattr(com, com_w)}")
                except ValueError:
                    setattr(com, com_w, default_value)

    def check_empty_and_set_default(self, var, default_value, v_type):
        """Controlla se il campo di input è vuoto e imposta il valore di default se non c'è focus"""
        input_value = var.get()
        if input_value == "":
            var.set(v_type(default_value) if v_type else default_value)
        else:
            try:
                if v_type == float:
                    value = float(input_value)
                    if value == float("inf") or value == float("-inf"):
                        raise ValueError("The value cannot be infinite.")
                    var.set(round(value, 2))
                elif v_type == int:
                    value = float(input_value)
                    if value == float("inf") or value == float("-inf"):
                        raise ValueError("The value cannot be infinite.")
                    var.set(int(value))
            except ValueError as e:
                var.set(v_type(default_value))
                messagebox.showerror("Error", str(e))
            except Exception as e:
                var.set(v_type(default_value))
                messagebox.showerror("Generic error", str(e))

    def browse_video(self):
        """Apre una finestra per selezionare un file video e aggiorna i percorsi."""
        try:
            video_file = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv")])
            if video_file:
                self.video_path.set(video_file)
                self.update_output_path()
                self.update_status(f"Video file loaded.: {com.video_path}", "static", 4)
                self.update_status(f"MIDI Output: {com.output_path}", "static", 4)
        except Exception as e:
            self.update_status(f"Video loading error: {str(e)}", "replace")

    def update_output_path(self):
        directory = self.video_path.get().replace("\\", "/")
        output_directory = os.path.join(os.path.dirname(os.path.dirname(directory)), "midi")
        os.makedirs(output_directory, exist_ok=True)
        video_name = os.path.splitext(os.path.basename(directory))[0]
        self.output_path.set(os.path.join(output_directory, f"{video_name}.mid").replace("\\", "/"))

    def browse_midi(self):
        try:
            output_dir = filedialog.asksaveasfilename(defaultextension=".mid", filetypes=[("MIDI Files", "*.mid")])
            if output_dir:
                self.output_path.set(output_dir)
                self.update_status(f"MIDI Output: {com.output_path}", "replace")
        except Exception as e:
            self.update_status(f"Error saving MIDI file: {str(e)}", "replace")

    def on_main_window_move(self, event):
        """Aggiorna la posizione della finestra di anteprima quando la finestra principale si muove."""
        if self.preview.preview_window and self.preview.preview_window.winfo_exists():
            x = self.root.winfo_x() + self.root.winfo_width()
            y = self.root.winfo_y()
            if (x != self.preview.current_preview_x) or (y != self.preview.current_preview_y):
                self.preview.preview_window.geometry(f"+{x}+{y}")
                self.preview.current_preview_x = x
                self.preview.current_preview_y = y

    def run_conversion(self):
        try:
            if not os.path.exists(com.video_path):
                raise ValueError("No video selected.") 
            if not (output_path := self.output_path.get()).endswith(".mid") or \
            not os.path.dirname(output_path) or \
            not os.path.basename(output_path)[:-4]:
                raise ValueError("No output path selected.") 
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.toggle_conversion()
            return
        except Exception as e:
            messagebox.showerror("Generic error", str(e))
            self.toggle_conversion()
            return

        try:
            def process_in_thread():
                try:
                    if self.preview.create_preview_window():
                        # Chiama process_video e controlla il risultato
                        result = self.converter.process_video(self.preview)
                        if result:
                            self.update_status("Conversion completed successfully.", "replace")
                        else:
                            raise ValueError("Conversion interrupted.")
                except ValueError as e:
                    messagebox.showerror("Error", str(e))
                except Exception as e:
                    messagebox.showerror("Generic error", str(e))

            # Esegui il processo di conversione in un thread separato
            threading.Thread(target=process_in_thread, daemon=True).start()

        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.toggle_conversion()
        except Exception as e:
            messagebox.showerror("Generic error", str(e))
            self.toggle_conversion()
            return False

    def toggle_conversion(self):
        """Avvia o interrompe la conversione"""
        if not self.process_stop_callback.is_set():
            self.process_stop_callback.set()
            self.convert_button.config(text="Stop Conversion")
            self.run_conversion()
        else:
            self.process_stop_callback.clear()
            self.convert_button.config(text="Start Conversion")

    def toggle_music(self):
        if self.music_playing:
            self.stop_music()
        else:
            self.play_music()

    def play_music(self):
        try:
            pygame.mixer.music.play(loops=-1)
            self.music_button.config(image=self.stop_photo)
            self.music_playing = True
        except pygame.error as e:
            messagebox(f"Audio loading error: {e}")

    def stop_music(self):
        pygame.mixer.music.stop()
        self.music_button.config(image=self.play_photo)
        self.music_playing = False

    def update_status(self, message, message_type, max_lines=3, temp=False, timer=3000):
        """Aggiorna l'etichetta di stato."""
        def handle_static():
            current_message = self.info_label.cget("text")
            new_message = f"{current_message}\n{message}" if current_message else message
            
            if len(new_message.split("\n")) > max_lines:
                return message
            return new_message

        def handle_replace():
            return message

        def handle_refresh():
            current_message = self.info_label.cget("text").split("\n")
            if current_message:
                last_line_word = current_message[-1].split()[-1]
                last_message_word = message.split()[-1]
                if last_line_word == last_message_word:
                    current_message.pop()
                return f"{"\n".join(current_message)}\n{message}" if current_message else message
            return message

        message_handlers = {
            "static": handle_static,
            "replace": handle_replace,
            "refresh": handle_refresh
        }

        new_message = message_handlers.get(message_type, lambda: "")()

        self.info_label.config(text=new_message)

        if temp:
            self.info_label.after(timer, lambda: self.info_label.config(text=""))

    def update_progress(self, progress):
        """Aggiorna la barra di progresso."""
        self.progress_bar["value"] = progress
        self.root.update_idletasks()

# Classe interfaccia anteprima
class Preview:
    def __init__(self, gui, stop_callback=None, status_callback=None):
        self.gui = gui
        self.stop_callback = stop_callback
        self.status_callback = status_callback

        self.preview_window = None
        self.preview_label = None
        self.current_preview_x = None
        self.current_preview_y = None

    def update_status(self, message, message_type, cancel=False):
        if self.status_callback:
            self.status_callback(message, message_type, cancel)
        # else:
        #     print(message)

    def image_preview(self):
        self.stop_callback.clear()
        
        def process_in_thread():
            try:
                # Chiama process_video e controlla il risultato
                result = self.generate_preview_image()
                if result:
                    self.update_preview_image()
                    self.update_status("Preview generation completed successfully.", "replace")
                else:
                    raise ValueError("Preview generation interrupted.")
            except ValueError as e:
                self.reset_preview_window()
                messagebox.showerror("Error", str(e))
                return
            except Exception as e:
                self.reset_preview_window()
                messagebox.showerror("Generic error", str(e))
                return

        if self.create_preview_window():
            threading.Thread(target=process_in_thread, daemon=True).start()

    def create_preview_window(self):
        try:
            if not os.path.exists(com.video_path):
                self.reset_preview_window()
                raise ValueError("No video selected.")
        except ValueError as e:
            messagebox.showwarning("Error", str(e))
            return
        except Exception as e:
            messagebox.showwarning("Generuc error", str(e))
            return
        
        try:
            if self.preview_window and tk.Toplevel.winfo_exists(self.preview_window):
                self.reset_preview_window()
            else:
                self.preview_window = tk.Toplevel(self.gui.root)
                self.preview_window.title("Preview")
                self.preview_window.geometry(f"600x430+{self.gui.root.winfo_x() + self.gui.root.winfo_width()}+{self.gui.root.winfo_y()}")
                # self.preview_window.attributes("-toolwindow", True)
                self.preview_window.overrideredirect(True)
                self.current_preview_x = self.preview_window.winfo_x()
                self.current_preview_y = self.preview_window.winfo_y()
                self.preview_window.protocol("WM_DELETE_WINDOW", self.on_preview_close)
                
                self.preview_label = ttk.Label(self.preview_window)
                self.preview_label.pack(expand=True)

                return True
        except Exception as e:
            messagebox.showerror("Generic error", f"Preview initialization failed.\n{ str(e)}")
            return False

    def update_preview_image(self):
        try:
            window_width = self.preview_window.winfo_width()
            window_height = self.preview_window.winfo_height()
            
            img = Image.open(com.preview_image)
            img = img.resize((window_width, window_height), Image.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)

            self.preview_label.imgtk = img_tk
            self.preview_label.config(image=img_tk)

            self.preview_window.bind("<Configure>", self.on_preview_configure)
            return True
        except (IOError, OSError) as e:
            messagebox.showerror("Error", f"Error loading preview image: {str(e)}")
        except Exception as e:
            messagebox.showerror("Generic error", {str(e)})

    def generate_preview_image(self):
        """Genera un'immagine di anteprima dal video senza iniziare la conversione MIDI."""        
        self.update_status("Generating preview...", "static", 3)
        
        vidcap = cv2.VideoCapture(com.video_path)

        try:
            success, image = vidcap.read()

            if not success:
                raise ValueError("Unable to open/read the video.")

            frame_height, frame_width, _ = image.shape
            fps = vidcap.get(cv2.CAP_PROP_FPS)

            com.keyboard_height = int(frame_height * com.keyboard_height)
            if com.keyboard_height >= frame_height:
                com.keyboard_height = frame_height - 1

            startFrame = int(com.start_frame * fps)
            vidcap.set(cv2.CAP_PROP_POS_FRAMES, startFrame)
            success, image = vidcap.read()

            if success:
                ia = np.asarray(image)
                kb = self.gui.converter.process_frame(ia, com.keyboard_height)

                self.gui.converter.extract_key_positions(kb)
                valid = self.gui.converter.label_keys() 

                if not valid:
                    raise ValueError("Invalid keys.")

                # Visualizzazione sul frame
                cv2.line(image, (0, com.keyboard_height), (frame_width, com.keyboard_height), (0, 255, 0), 2)
                for i in range(len(com.key_positions)):
                    color = (255, 255, 255) if com.default_values[i] < com.white_threshold else (0, 0, 0)
                    if i == com.middle_c:
                        cv2.rectangle(image, (com.key_positions[i] - 10, com.keyboard_height - 10), 
                        (com.key_positions[i] + 10, com.keyboard_height + 10), (0, 0, 255), -1)
                    else:
                        cv2.circle(image, (com.key_positions[i], com.keyboard_height), 7, color, -1)
                        cv2.circle(image, (com.key_positions[i], com.keyboard_height), 5, color, -1)

                    number_height = -75 if com.default_values[i] < com.white_threshold else +150
                    text = str(i)
                    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_COMPLEX, 0.75, 1)[0]
                    text_x = com.key_positions[i] - text_size[0] // 2
                    cv2.putText(image, text, (text_x, com.keyboard_height + number_height), 
                                cv2.FONT_HERSHEY_COMPLEX, 0.85, color, 1, cv2.LINE_AA)
                
                cv2.imwrite(com.preview_image, image)

                messagebox.showinfo("Success!", "Image preview generated successfully.")
            else:
                raise ValueError("Unable to generate the preview image.")
        except ValueError as e:
            self.stop_callback.clear()
            messagebox.showerror("Error", str(e))
            return False
        except Exception as e:
            self.stop_callback.clear()
            messagebox.showerror("Generic error", str(e))
            return False
        finally:
            vidcap.release()
            return True
        
    def reset_preview_window(self):
        """Resetta la finestra di anteprima chiudendola e reimpostando le variabili associate."""
        try:
            if self.preview_window and self.preview_window.winfo_exists():
                self.preview_window.destroy()
                self.preview_window = None
                self.preview_label = None
                self.current_preview_x = None
                self.current_preview_y = None
            else:
                return
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset the preview window.\n{str(e)}")

    def on_preview_configure(self, event):
        """Gestisce sia il ridimensionamento che lo spostamento della finestra di anteprima."""
        self.on_preview_window_move(event)
        self.on_preview_resize(event)

    def on_preview_close(self):
        """Gestisce la chiusura della finestra di anteprima."""
        if self.preview_window:
            self.reset_preview_window()

    def on_preview_window_move(self, event):
        """Aggiorna la posizione della finestra principale quando la finestra di anteprima si muove."""
        if self.preview_window and self.preview_window.winfo_exists():
            x = self.preview_window.winfo_x() - self.gui.root.winfo_width()
            y = self.preview_window.winfo_y()
            if (x != self.gui.current_main_x) or (y != self.gui.current_main_y):
                self.gui.root.geometry(f"+{x}+{y}")
                self.gui.current_main_x = x
                self.gui.current_main_y = y

    def on_preview_resize(self, event):
        """Aggiorna l'immagine della finestra di anteprima al ridimensionamento."""
        # print("Resizing")
        self.update_preview_image()

# Classe di conversione video in midi
class VideoToMidiConverter:
    def __init__(self, stop_callback=None, status_callback=None, progress_callback=None):
        self.stop_callback = stop_callback
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.note_on_frames = {}

    def update_status(self, message, message_type, cancel=False):
        if self.status_callback:
            self.status_callback(message, message_type, cancel)

    def update_progress(self, progress):
        if self.progress_callback:
            self.progress_callback(progress)

    def label_keys(self):
      """Imposta il tasto del Do centrale in base ai tasti scelti dall'utente."""
      # Controlla i valori di input
      if com.start_key < 0 or com.start_key > com.end_key:
          messagebox.showerror("Invalid keys. Make sure that Initial Key >= 0 and Initial Key < Final Key.")
          return False
      
      num_keys = com.end_key - com.start_key
      com.middle_c = com.start_key + (num_keys // 2) - 4

      self.update_status(f"Middle C set to key {com.middle_c}.", "static", 3)
      return True

    def get_pressed_keys(self, keys):
        """Restituisce l'elenco dei tasti premuti basato sulla luminosità."""
        pressed = []
        for i in range(len(keys)):
            if abs(keys[i] - com.default_values[i]) > com.threshold:
                pressed.append(1)  # Tasto premuto
            else:
                pressed.append(0)  # Tasto non premuto
        return pressed

    def extract_key_positions(self, keyboard):
        """Estrai le posizioni dei tasti basato sulla luminosità del frame."""
        inWhiteKey = False
        inBlackKey = False
        keyStart = 0
        maxBrightness = max(keyboard)
        minBrightness = min(keyboard)
        
        com.white_threshold = minBrightness + (maxBrightness - minBrightness) * 0.6
        com.black_threshold = minBrightness + (maxBrightness - minBrightness) * 0.4

        for i in range(len(keyboard)):
            b = keyboard[i]
            # Tasto bianco
            if b > com.white_threshold:
                if not inWhiteKey and not inBlackKey:
                    inWhiteKey = True
                    keyStart = i
            else:
                if inWhiteKey:
                    inWhiteKey = False
                    if i - keyStart > com.key_width:
                        position = int((keyStart + i) / 2)
                        com.key_positions.append(position)
                        com.default_values.append(keyboard[position])

            # Tasto nero
            if b < com.black_threshold:
                if not inBlackKey and not inWhiteKey:
                    inBlackKey = True
                    keyStart = i
            else:
                if inBlackKey:
                    inBlackKey = False
                    if i - keyStart > com.key_width:
                        position = int((keyStart + i) / 2)
                        com.key_positions.append(position)
                        com.default_values.append(keyboard[position])

        self.update_status(f"Detected {len(com.key_positions)} keys.", "static", 2)

    def process_frame(self, ia, keyboard_height):
        """Elabora un singolo frame e restituisce la luminosità della tastiera."""
        kb = []
        for x in range(len(ia[0])):
            kb.append(np.mean(ia[keyboard_height][x]))  # Calcola la media dei pixel sulla riga della tastiera
        return kb

    def process_video(self, preview):
        """Elabora il video per estrarre i tasti premuti e creare un file MIDI."""
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)

        vidcap = cv2.VideoCapture(com.video_path)

        try:
            success, image = vidcap.read()

            if not success:
                messagebox.showerror("Error", f"Unable to open/read the video: {com.video_path}")
                return

            frame_height, frame_width, _ = image.shape
            fps = vidcap.get(cv2.CAP_PROP_FPS)
            self.update_status(f"Processing video at {frame_height}p@{fps} FPS...", "replace")

            com.keyboard_height = int(frame_height * com.keyboard_height)
            if com.keyboard_height >= frame_height:
                com.keyboard_height = frame_height - 1

            startFrame = int(com.start_frame * fps)  # Inizio del video
            endFrame = int(com.end_frame * fps) if com.end_frame > 0 else int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))  # Fine del video

            count = 0
            lastPressed = []
            lastMod = 0
            active_notes = {}
            ms_per_frame = 1000 / fps

            while success:
                if not self.stop_callback.is_set():
                    self.update_status("Conversion interrupted.", "replace")
                    return False
                
                ia = np.asarray(image)
                kb = self.process_frame(ia, com.keyboard_height)

                if count == startFrame:
                    self.extract_key_positions(kb)
                    valid = self.label_keys()
                    lastPressed = [0] * len(com.key_positions)

                    if not valid: 
                        return
                    
                if count >= startFrame:
                    keys = [kb[com.key_positions[i]] for i in range(len(com.key_positions))]
                    pressed = self.get_pressed_keys(keys)

                    for i in range(len(pressed)):
                        if pressed[i] != lastPressed[i]:  # Se lo stato del tasto è cambiato
                            note = 60 - com.middle_c + i
                            if pressed[i] == 1:
                                # Calcoliamo il tempo trascorso dall'ultimo evento (anche se era un tempo di inattività)
                                if lastMod != count:
                                    inactivity_duration = int((count - lastMod) * ms_per_frame)
                                    lastMod = count
                                else:
                                    inactivity_duration = 0
                                
                                # Aggiungiamo il messaggio note_on
                                track.append(Message('note_on', note=note, velocity=64, time=inactivity_duration))
                                active_notes[note] = count  # Memorizziamo il tempo di inizio della nota
                                # print(f"{i}: Note ON | count: {count} | fps: {fps} | Inactivity Duration: {inactivity_duration} ms")
                            
                            elif pressed[i] == 0 and note in active_notes:
                                note_duration = int((count - active_notes[note]) * ms_per_frame)
                                track.append(Message('note_off', note=note, velocity=127, time=note_duration))
                                lastMod = count  # Aggiorniamo lastMod al momento attuale
                                del active_notes[note]
                                # print(f"{i}: Note OFF | count: {count} | Duration: {note_duration} ms")
                        
                    lastPressed = pressed

                    progress = (count - startFrame) / (endFrame - startFrame) * 100
                    self.update_progress(progress)
                    self.update_status(f"Processing frame {count} / {endFrame}...", "refresh")


                # Visualizzazione sul frame
                cv2.line(image, (0, com.keyboard_height), (frame_width, com.keyboard_height), (0, 255, 0), 2)
                for i in range(len(com.key_positions)):
                    color = (255, 255, 255) if com.default_values[i] < com.white_threshold else (0, 0, 0)

                    if i == com.middle_c:
                        cv2.rectangle(image, (com.key_positions[i] - 10, com.keyboard_height - 10), 
                        (com.key_positions[i] + 10, com.keyboard_height + 10), (0, 0, 255), -1)
                    else:
                        # Cambia colore se il tasto è premuto
                        if lastPressed[i] == 1:
                            color = (0, 255, 0)
                        else:  # Tasto non premuto
                            color = (255, 255, 255) if com.default_values[i] < com.white_threshold else (0, 0, 0)

                        cv2.circle(image, (com.key_positions[i], com.keyboard_height), 7, color, -1)
                        cv2.circle(image, (com.key_positions[i], com.keyboard_height), 5, color, -1)

                    number_height = -75 if com.default_values[i] < com.white_threshold else +150
                    text = str(i)
                    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_COMPLEX, 0.75, 1)[0]
                    text_x = com.key_positions[i] - text_size[0] // 2
                    cv2.putText(image, text, (text_x, com.keyboard_height + number_height), 
                                cv2.FONT_HERSHEY_COMPLEX, 0.85, color, 1, cv2.LINE_AA)
                cv2.imwrite(com.preview_image, image)
                preview.update_preview_image()

                success, image = vidcap.read()
                count += 1

                if count > endFrame and endFrame > 0:
                    break

            mid.save(com.output_path)
            self.update_status(f"MIDI file saved as: {com.output_path}", "replace")
            messagebox.showinfo("Success", f"MIDI file saved as: {com.output_path}")

            return True
        finally:
            vidcap.release()

if __name__ == "__main__":
    root = tk.Tk()
    root_font = font.nametofont("TkDefaultFont")
    root_font.configure(family="Roman", size="10")
    com = Com()
    app = Gui(root)
    root.mainloop()
