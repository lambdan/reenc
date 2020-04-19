So you have a folder with videos that you don't really care that much about so you wanna make them smaller but not sacrifice too much quality? This is for you.
I wouldn't recommend re-doing your entire Plex library using this, but maybe for some shows you don't care about anymore and can easily get new copies of if needed.

- Only tested on Windows, probably works on Unix with minor tweaks
- Highly recommend changing settings in the settings section, such as path, delete original files or not, target bitrates, etc.

# Requirements

- [other-transcode](https://github.com/donmelton/other_video_transcoding)
- [ffmpeg & ffprobe](https://ffmpeg.zeranoe.com/builds/)
- NVIDIA GPU with HEVC 10-bit encoding support (GTX 10XX+?)
	- Unless you disable nvenc/10-bit and just use whatever you can use... (modify the `ot_settings` line)
