So you have a folder with videos that you don't really care that much about so you wanna make them smaller but not sacrifice too much quality? This is for you.
I wouldn't recommend re-doing your entire Plex library using this, but maybe for some shows you don't care about anymore and can easily get new copies of if needed.

There are two versions:

`reenc_windows_nvenc.py` = This is meant for use on Windows with NVIDIA GPU's supporting NVENC

`reenc_mac_vt.py` = This is meant for Mac users with a Mac that supports VideoToolbox HEVC encoding (like M1 Macs)

It's highly recommend changing settings in the settings section, such as path, delete original files or not, target bitrates, etc. It should be pretty self explanatory.

# Requirements

- Python 3
- [other-transcode](https://github.com/donmelton/other_video_transcoding)
- [ffmpeg & ffprobe](https://ffmpeg.zeranoe.com/builds/)