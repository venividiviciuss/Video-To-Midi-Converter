# VideoToMidiConverter

⚠️ Warning: The code is still under development and may not function as expected. ⚠️


VideoToMidiConverter is an advanced tool written in Python to convert videos of musical keyboards into MIDI files. By utilizing video frame processing, the program identifies the keys pressed on the keyboard based on brightness and generates the corresponding MIDI file. It also includes an interactive graphical user interface (GUI) that allows users to dynamically manipulate parameters to adapt the converter to different types of videos, making the program versatile and easily adaptable to various contexts of use.

![image](https://github.com/user-attachments/assets/9f9aea49-7d1a-42a8-b844-583ead533d6d)

## Key Features:
- **Automatic Keyboard Detection:** The program analyzes the video frames to identify the positions of the white and black keys.
- **MIDI Note Extraction:** It detects and records when keys are pressed and released, generating corresponding MIDI notes.
- **Integrated GUI:** The graphical interface allows users to monitor the status of the conversion, the progression of frames, and view a preview of the processed video. Parameters can be easily adjusted to tailor the converter to various video types, optimizing the accuracy of the transcription.
- **Preview Window:** During video processing, users can view a real-time preview of the detected keys and notes.

## How It Works:
1. Upload a video of a musical keyboard.
2. Set the parameters, such as the initial key and final key based on those present in the video, and the start time and end time according to your preferences.
3. The program automatically identifies the positions of the keys based on brightness.
4. It converts each frame into a series of MIDI notes, distinguishing when a key is pressed and released.
5. It saves the result in a MIDI file, ready to be used with any digital music software.

This tool is ideal for musicians and developers looking to automate the transcription of musical performances into MIDI format from keyboard videos.

## How to Use the Project:
1. **Install the required dependencies:**
   Make sure you have Python installed on your system. Then, navigate to the project directory and run:
   ```bash
   pip install -r requirements.txt
   ```
   
   Alternatively, you can install the dependencies directly using:
   ```bash
   pip install opencv-python Pillow numpy mido pygame
   ```

2. **Run the application:**
   You can start the application by executing:
   ```bash
   python main.py
   ```

3. **Upload Your Video:**
   Ensure that the video file is of good quality and clearly shows the keyboard being played. Videos shot in good lighting conditions work best.

4. **Set Parameters:**
   Adjust the initial key and final key based on those present in the video. This helps the program focus on the relevant keys.
   Set the start time and end time to limit the section of the video you want to convert, which can improve performance.
   Use the Preview Window: During the conversion, use the preview window to monitor which keys are being detected in real time. This can help you verify that the program is       correctly interpreting the video.

5. **Experiment with Settings:**
   Depending on the video, you may need to experiment with different settings (like the activation threshold) to optimize the accuracy of the MIDI conversion.

6. **Save Your Work:**
   After conversion, ensure you save the resulting MIDI file properly. Test it in your preferred digital audio workstation (DAW) to check the results.

## Credits
Developed by **venividiviciuss**  
Copyright © 2024-2025

Thanks for any support and improvements you may offer. If you would like to donate, please visit: *****
