import cv2
import numpy as np
import threading
import time
from mido import Message, MidiFile, MidiTrack
import os

class VideoProcessor:
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self.start_frame = 0
        self.end_frame = self.frame_count
        
        # Detection configuration
        self.keyboard_y = 0.75 # Fraction of the height
        self.detection_height = 10 # Height in pixels of the detection area
        self.threshold = 30
        self.start_key = 21 # MIDI Note
        self.end_key = 108 # 88 keys (A0 - C8)
        self.key_positions = []
        self.white_threshold = 127
        self.black_threshold = 127
        self.base_brightness = []
        
        # Midi settings
        self.bpm = 120
        self.use_quantization = False
        self.quantization_value = "1/16"
        
        # Separate thresholds for white and black keys
        self.white_threshold_factor = 0.7
        self.black_threshold_factor = 0.3
        
        # Manual Mode
        self.use_manual_mode = False
        self.manual_keys = [] # List of {'x': x, 'y': y, 'w': w, 'h': h, 'type': 'manual'}
        
        # Color Filtering (HSV)
        self.use_color_filter = False
        self.hsv_min = np.array([0, 0, 200]) # Default white/bright
        self.hsv_max = np.array([180, 255, 255])
        self.filter_iterations = 1 # Erode/Dilate iterations to remove noise
        self.dilate_iterations = 0 # Dilate iterations to "expand" notes
        self.show_binary_mask = False # Show mask in binary (black/white) vs original colors
        
        # New filters and image adjustments
        self.contrast = 1.0 # alpha
        self.brightness = 0.0 # beta
        self.gamma = 1.0
        self.blur_size = 0 # Gaussian blur kernel size
        self.invert_mask = False
        self.edge_detection = False # Canny edge detection
        self.use_contour_filling = False # Fill contours to create solid notes
        self.contour_color = (0, 255, 0) # BGR: Green by default
        self.min_contour_area = 20 # Minimum area in pixels to keep a contour
        self.use_intelligent_filter = False # Filter by shape/aspect ratio
        self.min_aspect_ratio = 1.5 # Min H/W for a falling note
        
        # Note names for display
        self.show_note_names = False
        self.note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    def midi_to_note_name(self, midi_number):
        """Converts MIDI note number to note name (e.g., 60 -> C4)."""
        octave = (midi_number // 12) - 1
        note_idx = midi_number % 12
        return f"{self.note_names[note_idx]}{octave}"

    def apply_color_filter(self, frame):
        if not self.use_color_filter:
            return frame
            
        # 1. Basic image adjustments (Contrast/Brightness)
        # alpha = contrast, beta = brightness
        frame_adj = cv2.convertScaleAbs(frame, alpha=self.contrast, beta=self.brightness)
        
        # 2. Gamma correction
        if self.gamma != 1.0:
            inv_gamma = 1.0 / self.gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
            frame_adj = cv2.LUT(frame_adj, table)

        # 2b. Edge Detection (optional)
        if self.edge_detection:
            gray = cv2.cvtColor(frame_adj, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            # Convert back to BGR to allow combined operations if needed, 
            # or just use it to enhance the frame
            edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            frame_adj = cv2.addWeighted(frame_adj, 0.7, edges_bgr, 0.3, 0)
        
        # 3. Gaussian Blur to reduce noise/sparkles
        if self.blur_size > 0:
            # Ensure blur_size is odd
            k_size = self.blur_size * 2 + 1
            frame_adj = cv2.GaussianBlur(frame_adj, (k_size, k_size), 0)
            
        # 4. HSV Filtering
        hsv = cv2.cvtColor(frame_adj, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.hsv_min, self.hsv_max)
        
        # 5. Invert mask if requested
        if self.invert_mask:
            mask = cv2.bitwise_not(mask)
        
        # 6. Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        if self.filter_iterations > 0:
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=self.filter_iterations)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=self.filter_iterations)

        # 6b. Extra Dilate to expand thin edges/notes
        if self.dilate_iterations > 0:
            mask = cv2.dilate(mask, kernel, iterations=self.dilate_iterations)

        # 7. Apply mask to keep original colors or show binary
        if self.use_contour_filling:
            # Create a black background image
            filtered = np.zeros_like(frame_adj)
            # Find contours on the binary mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by minimum area (to remove small particles)
            filtered_contours = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < self.min_contour_area:
                    continue
                
                if self.use_intelligent_filter:
                    # Falling notes are usually vertical rectangles
                    x, y, w, h = cv2.boundingRect(cnt)
                    aspect_ratio = float(h) / w
                    # Check if it's "note-like" (vertical and relatively rectangular)
                    # Note: particles are often circular or scattered
                    if aspect_ratio < self.min_aspect_ratio:
                        continue
                    # Rectangularity check: area / (w*h) should be high
                    rect_area = w * h
                    if rect_area > 0:
                        rectangularity = area / rect_area
                        if rectangularity < 0.5: # At least 50% of the bounding box
                            continue
                
                filtered_contours.append(cnt)
                
            # Draw filtered contours filled with solid chosen color
            cv2.drawContours(filtered, filtered_contours, -1, self.contour_color, thickness=-1)
        elif self.show_binary_mask:
            # Show the mask itself as a grayscale/BGR image
            filtered = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        else:
            # Apply mask to keep original colors but black out everything else
            filtered = cv2.bitwise_and(frame_adj, frame_adj, mask=mask)
        
        return filtered

    def get_frame(self, frame_idx=0):
        # Always set position to ensure we get exactly that frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret:
            return self.apply_color_filter(frame)
        return None

    def analyze_keyboard(self, frame):
        # Frame is already filtered by get_frame or should be filtered here if passed directly
        # To be safe, we apply filter if it's not already (though usually it is)
        # But if we want to see the effect in real-time, it's better if the caller handles it.
        # For consistency, we assume frame passed here is the "raw" frame from video or filtered.
        y_px = int(self.height * self.keyboard_y)
        h_half = self.detection_height // 2
        y_start = max(0, y_px - h_half)
        y_end = min(self.height, y_px + h_half + 1)
        
        # Extract the keyboard area and calculate average brightness for each column
        kb_area = frame[y_start:y_end, :, :]
        kb_line = np.mean(np.mean(kb_area, axis=2), axis=0)

        if self.use_manual_mode:
            # In manual mode, positions are pre-defined as regions
            self.key_positions = []
            for m_key in self.manual_keys:
                x, y, w, h = m_key['x'], m_key['y'], m_key['w'], m_key['h']
                
                # Extract the box area
                y_start, y_end = max(0, y), min(self.height, y + h)
                x_start, x_end = max(0, x), min(self.width, x + w)
                
                if y_end > y_start and x_end > x_start:
                    box_area = frame[y_start:y_end, x_start:x_end, :]
                    brightness = np.mean(box_area)
                    
                    self.key_positions.append({
                        'x': x, 'y': y, 'w': w, 'h': h,
                        'pos': x + w // 2, # for C4 identification if needed
                        'type': 'manual', 
                        'brightness': brightness
                    })
            
            # Use current brightness as base_brightness if not already set or if calibrating
            if not self.base_brightness or len(self.base_brightness) != len(self.key_positions):
                self.base_brightness = [k['brightness'] for k in self.key_positions]
                
            return len(self.key_positions)
        
        self.key_positions = []
        self.base_brightness = []
        
        # Dynamic calculation of local threshold to better detect keys
        # Instead of a global threshold, we use a moving average or edge gradient
        
        max_b = np.max(kb_line)
        min_b = np.min(kb_line)
        self.white_threshold = min_b + (max_b - min_b) * self.white_threshold_factor
        self.black_threshold = min_b + (max_b - min_b) * self.black_threshold_factor
        
        in_white = False
        in_black = False
        start_idx = 0
        
        # First pass: White keys detection (brightness peaks)
        for i in range(len(kb_line)):
            is_white = kb_line[i] > self.white_threshold
            if is_white:
                if not in_white:
                    in_white = True
                    start_idx = i
            else:
                if in_white:
                    in_white = False
                    if i - start_idx > 3: # Noise filter
                        pos = (start_idx + i) // 2
                        self.key_positions.append({'pos': pos, 'type': 'white', 'brightness': kb_line[pos]})
        
        # Handle last key if white and touching the edge
        if in_white:
            if len(kb_line) - start_idx > 3:
                pos = (start_idx + len(kb_line)) // 2
                self.key_positions.append({'pos': pos, 'type': 'white', 'brightness': kb_line[pos-1]})

        # Second pass: Black keys detection (brightness valleys)
        for i in range(len(kb_line)):
            is_black = kb_line[i] < self.black_threshold
            if is_black:
                if not in_black:
                    in_black = True
                    start_idx = i
            else:
                if in_black:
                    in_black = False
                    if i - start_idx > 2: # Noise filter
                        pos = (start_idx + i) // 2
                        self.key_positions.append({'pos': pos, 'type': 'black', 'brightness': kb_line[pos]})

        # Handle last key if black and touching the edge
        if in_black:
            if len(kb_line) - start_idx > 2:
                pos = (start_idx + len(kb_line)) // 2
                self.key_positions.append({'pos': pos, 'type': 'black', 'brightness': kb_line[pos-1]})
        
        # Sort key positions from left to right
        self.key_positions.sort(key=lambda x: x['pos'])
        
        # Recalculate base_brightness for consistency with the rest of the code (if needed)
        self.base_brightness = [k['brightness'] for k in self.key_positions]
        
        return len(self.key_positions)

    def get_c4_index(self):
        """Attempts to identify the index of C4 (MIDI 60) among detected keys."""
        # If no keys are found, we cannot calculate anything
        if not self.key_positions:
            return -1
        
        # Assuming the first key is self.start_key
        # C4 (MIDI 60) is the offset 60 - self.start_key
        c4_midi = 60
        idx = c4_midi - self.start_key
        
        if 0 <= idx < len(self.key_positions):
            return idx
        return -1

    def convert_to_midi(self, output_path, progress_callback=None, status_callback=None, frame_callback=None, stop_event=None):
        # We need to access get_text from main if possible, or just use it here if we import it.
        # But to avoid circular imports, let's just use the callbacks and pass pre-formatted strings from main or just keys.
        # However, to maintain current structure let's import it here.
        from main import get_text as get_t
            
        mid = MidiFile()
        track = MidiTrack()
        mid.tracks.append(track)
        
        # MIDI Timing (based on previous fixes and set BPM)
        ticks_per_beat = 480
        bpm = self.bpm
        tempo = 60000000 / bpm
        ms_per_tick = tempo / (ticks_per_beat * 1000)
        ms_per_frame = 1000 / self.fps
        
        # Mapping musical values to ticks (ticks_per_beat = 480, which is a quarter note 1/4)
        # Whole note 4/4 = 1920
        # Half note 2/4 = 960
        # Quarter note 1/4 = 480
        # Eighth note 1/8 = 240
        # Sixteenth note 1/16 = 120
        # Thirty-second note 1/32 = 60
        # Sixty-fourth note 1/64 = 30
        quant_map = {
            "1/1": 1920, "1/2": 960, "1/4": 480, 
            "1/8": 240, "1/16": 120, "1/32": 60, "1/64": 30
        }
        quantization_ticks = quant_map.get(self.quantization_value, 120) if self.use_quantization else 1
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
        
        # First pass to calibrate positions if not already done
        if not self.key_positions:
            ret, frame = self.cap.read()
            if not ret: return False
            self.analyze_keyboard(frame)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
            
        num_keys = len(self.key_positions)
        last_pressed = [0] * num_keys
        active_notes = {}
        last_event_frame = self.start_frame
        
        # Debounce and stability: Track confirmed state and consecutive frames
        confirmed_pressed = [0] * num_keys
        consecutive_frames = [0] * num_keys
        debounce_limit = 2 # Minimum number of frames to confirm state change
        
        y_px = int(self.height * self.keyboard_y)
        h_half = self.detection_height // 2
        y_start = max(0, y_px - h_half)
        y_end = min(self.height, y_px + h_half + 1)
        c4_idx = self.get_c4_index()
        
        total_frames_to_process = self.end_frame - self.start_frame
        
        for count in range(self.start_frame, self.end_frame):
            if stop_event and stop_event.is_set(): break
            
            ret, frame = self.cap.read()
            if not ret: break
            
            kb_line = None
            if not self.use_manual_mode:
                kb_area = frame[y_start:y_end, :, :]
                kb_line = np.mean(np.mean(kb_area, axis=2), axis=0)
            
            for i, key_info in enumerate(self.key_positions):
                if self.use_manual_mode:
                    x, y, w, h = key_info['x'], key_info['y'], key_info['w'], key_info['h']
                    # Use predefined areas
                    y_s, y_e = max(0, y), min(self.height, y + h)
                    x_s, x_e = max(0, x), min(self.width, x + w)
                    if y_e > y_s and x_e > x_s:
                        brightness = np.mean(frame[y_s:y_e, x_s:x_e, :])
                    else:
                        brightness = self.base_brightness[i]
                else:
                    pos = key_info['pos']
                    brightness = kb_line[pos]
                
                # Instant detection
                is_pressed_now = abs(brightness - self.base_brightness[i]) > self.threshold
                
                # Debounce Logic: State change must last at least debounce_limit frames
                if is_pressed_now != confirmed_pressed[i]:
                    consecutive_frames[i] += 1
                    if consecutive_frames[i] >= debounce_limit:
                        # State change CONFIRMED
                        confirmed_pressed[i] = is_pressed_now
                        consecutive_frames[i] = 0
                        
                        # Send MIDI event if the state has changed since the last event sent
                        if confirmed_pressed[i] != last_pressed[i]:
                            note = self.start_key + i
                            delta_ms = (count - last_event_frame) * ms_per_frame
                            delta_ticks = int(delta_ms / ms_per_tick)
                            
                            if confirmed_pressed[i]:
                                # If quantization is active, round delta_ticks to nearest sixteenth note
                                if self.use_quantization:
                                    delta_ticks = round(delta_ticks / quantization_ticks) * quantization_ticks
                                
                                track.append(Message('note_on', note=note, velocity=64, time=delta_ticks))
                                active_notes[note] = count
                            else:
                                if self.use_quantization:
                                    delta_ticks = round(delta_ticks / quantization_ticks) * quantization_ticks
                                
                                track.append(Message('note_off', note=note, velocity=127, time=delta_ticks))
                                if note in active_notes: del active_notes[note]
                                
                            last_event_frame = count
                            last_pressed[i] = confirmed_pressed[i]
                else:
                    consecutive_frames[i] = 0 # Reset if the state returns to the confirmed one
            
            # Runtime Preview (frame callback)
            if frame_callback and count % 2 == 0: # Update every 2 frames for performance
                preview_img = frame.copy()
                
                if self.use_manual_mode:
                    for i, key_info in enumerate(self.manual_keys):
                        x, y, w, h = key_info['x'], key_info['y'], key_info['w'], key_info['h']
                        cv2.rectangle(preview_img, (x, y), (x + w, y + h), (0, 255, 255), 2)
                        # Note index/number or name for reference
                        midi_note = self.start_key + i
                        text_label = self.midi_to_note_name(midi_note) if self.show_note_names else str(midi_note)
                        cv2.putText(preview_img, text_label, (x + 2, y + 15), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
                else:
                    cv2.line(preview_img, (0, y_px), (self.width, y_px), (0, 255, 0), 2)

                for i, key_info in enumerate(self.key_positions):
                    # Base color: use confirmed_pressed for runtime preview for visual stability
                    if confirmed_pressed[i]:
                        color = (0, 255, 0) # Green if pressed
                    else:
                        if self.use_manual_mode:
                            color = (0, 255, 255) # Cyan if manual
                        else:
                            is_white = key_info['type'] == 'white'
                            color = (60, 60, 60) if is_white else (255, 255, 255)
                    
                    if self.use_manual_mode:
                        x, y, w, h = key_info['x'], key_info['y'], key_info['w'], key_info['h']
                        pos_x, pos_y = x + w // 2, y + h // 2
                    else:
                        pos_x, pos_y = key_info['pos'], y_px

                    if i == c4_idx:
                        cv2.circle(preview_img, (pos_x, pos_y), 8, (0, 0, 255), -1)
                        cv2.putText(preview_img, "C4", (pos_x - 10, pos_y - 15), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    
                    cv2.circle(preview_img, (pos_x, pos_y), 5, color, -1)
                
                frame_callback(preview_img)

            if status_callback and count % 5 == 0:
                status_callback(count - self.start_frame, total_frames_to_process)

            if progress_callback and count % 10 == 0:
                progress_callback((count - self.start_frame) / total_frames_to_process)
                
        mid.save(output_path)
        return not (stop_event and stop_event.is_set())

    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()
