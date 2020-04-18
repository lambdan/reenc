- Only tested on Windows, probably works on Unix with minor tweaks
- Highly recommend changing settings in the settings section, such as path, delete original files or not, target bitrates, etc.

# Requirements

- [other-transcode-](https://github.com/donmelton/other_video_transcoding)
- [ffmpeg](https://ffmpeg.zeranoe.com/builds/)
- NVIDIA GPU with HEVC 10-bit encoding support (GTX 10XX+?)
	- Unless you disable nvenc/10-bit and just use whatever you can use... (modify the `ot_settings` line)
