# Video to MIDI Converter v2

⚠️ **Development Note**: This version is a significant upgrade over v1. While more stable, it is still a passion project. Feedback is always welcome! 🎹✨

**Video to MIDI Converter v2** is an advanced Python-based utility designed to transform video recordings of piano performances (Synthesia-style or top-down views) into precise MIDI files. By leveraging real-time frame processing and a revamped detection algorithm, v2 offers professional-grade accuracy with a modern, user-friendly interface.

## 🚀 Key Features
- **Modern GUI**: A sleek, responsive interface built with CustomTkinter for a professional user experience.
- **Live Calibration Preview**: Adjust keyboard height and detection thresholds in real-time before starting the conversion.
- **Intelligent Detection Engine**: Optimized algorithms for both white and black keys, featuring a *debounce filter* to eliminate "ghost notes" and flickering.
- **C4 Visual Reference**: Automatic highlighting of Middle C (C4) to ensure your MIDI mapping is perfectly aligned.
- **Advanced "Shader" Filter**: A powerful video filtering system to isolate notes and remove visual noise (particle effects, reflections).
- **HSV Color Filtering**: Isolate specific colors (Red, Blue, Green, etc.).
- **Image Adjustments**: Contrast, Brightness, and Gamma correction.
- **Noise Reduction**: Gaussian Blur and Morphological operations (Erosion/Dilation).
- **Edge Detection**: Optional Canny Edge detection to highlight note outlines.
- **Advanced Manual Mode**: Create, resize, and move custom detection boxes directly on the video.
- **Async Processing**: Smooth, non-blocking conversion with a real-time runtime preview and progress tracking.
- **Musical Quantization**: Align notes to a musical grid (e.g., 1/16, 1/4) to correct timing inconsistencies automatically.
- **Advanced Logging**: Integrated system logs (logs.log) for easy debugging and activity tracking.

💡 **Important note**:

The program works quite well with very simple videos, 
where the piano is clearly visible and there are not many visual effects. 
For videos with complex particle effects, unusual colors, or hands covering the keys, 
even the most advanced filters may not guarantee a perfect conversion.

## 🛠️ Requirements
- **Python 3.8+**
- **OpenCV** (Image processing)
- **NumPy** (Data calculation)
- **Mido** (MIDI file generation)
- **Pillow** (Image handling)
- **CustomTkinter** (Modern UI)

## 📦 Installation
1. **Clone or enter the project directory**:
   ```bash
   cd Video-To-Midi-Converter
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🎹 How to Use
1. **Launch the App**:
   ```bash
   python main.py
   ```
2. **Load Video**: Select your piano performance video file.
3. **Calibration**: 
   - Adjust the *Keyboard Height* slider until the green line sits perfectly across the center of the keys.
   - Set the *Starting MIDI Note* (Default is 21 for a standard 88-key A0 piano).
   - Verify that the red *C4* dot aligns with Middle C in your video.
4. **Threshold & Sensitivity**: 
   - Fine-tune the *Detection Threshold* to capture notes accurately.
   - Use the *Black/White Sensitivity* factors (typically 0.7 for White, 0.3 for Black) to compensate for different lighting or key reflections.
5. **BPM & Quantization**: 
   - Input the *BPM* of the song.
   - Enable *Quantize* if you want the notes to snap to the nearest musical beat (e.g., 1/16 for sixteenth notes).
6. **Convert**: Hit the start button, choose your save location, and watch the progress in the preview window.

### 🎨 Using the Filter (Shader)
For videos with complex particle effects or gradients:
1. Go to the **Filter** tab and enable **Use Color Filter (HSV)**.
2. Use **Min/Max Sliders** to isolate the color of the notes (e.g., Hue for color type, Value for brightness).
3. Use **Contrast (alpha)** and **Brightness (beta)** to separate notes from the background.
4. If notes have gaps or thin edges (gradient notes), increase **Dilate (Expand Notes)** in the **Noise** sub-tab.
5. Toggle **Show Binary Mask** to see exactly what the computer is "seeing" (white pixels will be detected).
6. Enable **Edge Detection** to highlight note outlines if necessary.

## 📝 Note Calibration Guide (MIDI ID)
Setting the correct starting note is crucial for an accurate transcription:
- **21**: Standard 88-key piano (starts at A0)
- **36**: 61-key keyboard (starts at C2)
- **60**: Central octave only (starts at C4)

## 🤝 Credits & Support
Developed with passion by venividiviciuss

Copyright © 2024-2026

If this tool helped you in your musical journey, consider supporting the project:
☕ [Donate with PayPal](https://www.paypal.com/donate?hosted_button_id=BXRRJU2XAVPB4)

---------------------------------------------------------------------------------

Developed for musicians, by a developer who loves music.
