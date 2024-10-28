# Changelog for VideoToMidiConverter

## [0.0.1] - 2024-10-28
### Initial Alpha
- First pre-release of VideoToMidiConverter.

### Added
- Initial setup of the project.
- Interactive GUI for video loading and parameter settings.

### Changed
- Improved video processing algorithm for better key detection.
- Updated parameter settings for more flexibility in MIDI generation.

### Fixed
---

### Known Issues
**IMPORTANT**
- The note generation is not well defined for the duration timing.
- Lack of BPM definition; an automatic calculation function will be added.
- Very slow conversion process due to preview. Approx: 1 frame per second... 
- Something else I don't know or don't remember yet *.*

**LESS IMPORTANT**
- Starting and then stopping the conversion causes a bug, preventing the program from being reused. It is necessary to restart the program for a new use. xD
- You may experience occasional flash issues while processing video in the preview window, which are not a cause for concern.
- Something else I don't know or don't remember yet *.*
