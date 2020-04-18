import sys, os, shutil
import subprocess
import json
import hashlib
import datetime

# settings !

delete_original = False # if True, source files will be deleted! dangerous!!!
input_path = 'Z:/Video/' # folder with videos to batch through (also goes through subfolders)
minimum_video_bitrate = 4000 # videos with lower/equal bitrate to this will be skipped (kbps)
minimum_video_height = 720 # videos with lower/equal resolution to this will be skipped
ot = os.path.abspath(os.path.join('C:/Ruby27-x64/bin', 'other-transcode.bat')) # path to other-transcode.bat (Windows is great, isn't it).. on unix i think you can just change this line to ` ot = 'other-transcode' ` ?
ot_settings = '--crop auto --nvenc --10-bit --hevc' # these are passed to other-transcode
output_video_extension = 'mp4' # mp4 or mkv

# target video bitrates in kbps
target_480p = 500
target_720p = 1000
target_1080p = 2500
target_2160p = 7000

VALID_VIDEO_EXTENSIONS = ('mp4','wmv','avi','flv','m4v','mkv','mpg')
VALID_FILENAME_SYMBOLS = [',', '.', '[', ']', ' ', '(', ')', '-', '_']

# end of settings



print ('*** Settings ***')
print ('Folder to process:', input_path)
print ('Delete original:', delete_original)
print ('Minimum bitrate:', minimum_video_bitrate)
print ('Minimum video resolution:', minimum_video_height)
print ('Additional other-transcode settings:', ot_settings)
print ('Video extension for output:', output_video_extension)
print ('Target video bitrates:')
print ('\t480p:', target_480p)
print ('\t720p:', target_720p)
print ('\t1080p:', target_1080p)
print ('\t2160p:', target_2160p)
print ('\n')

def get_stream(json, which):
	for stream in json['streams']:
		if stream['codec_type'] == which: # audio or video (or subtitle?)
			return stream
	return 'No_' + which 

def md5_string(string):
	hash_object = hashlib.md5(string.encode())
	return hash_object.hexdigest()

def get_info(json, what):
	# json should be from ffprobe
	if what == 'duration_HHMMSSXXX':
		secs = float(json['format']['duration'])
		a = datetime.timedelta(seconds=secs) # https://stackoverflow.com/a/1384417
		return str(a) 

	if what == 'size': # file size in bytes
		return int(json['format']['size'])

	if what == 'sizeMB': # file size in MB
		return int(json['format']['size']) / 1000000

	if what == 'vresolution': # 1920x1080 etc.
		return str(get_stream(json, 'video')['width']) + 'x' + str(get_stream(json, 'video')['height'])

	if what == 'vcodec': # h264 mpeg etc.
		return get_stream(json, 'video')['codec_name']

	if what == 'vfps':
		fffps = get_stream(json, 'video')['r_frame_rate'] # "30/1"
		div = fffps.split('/')
		return round(float(div[0])/float(div[1]),3)

	if what == 'acodec': # aac mp3 etc.
		return get_stream(json, 'audio')['codec_name']

	if what == 'a_channel_layout': # stereo mono etc.
		return get_stream(json, 'audio')['channel_layout']

	if what == 'achannels': # 1, 2, etc
		return int(get_stream(json, 'audio')['channels'])

	if what == 'a_bitrate_kbits': # audio bitrate in kbit
		try:
			return int(get_stream(json, 'audio')['bit_rate'])/1000
		except:
			return 99999999999

	if what == 'width': # 1920 etc.
		return int(get_stream(json, 'video')['width'])

	if what == 'height': # 1080 etc.
		return int(get_stream(json, 'video')['height'])

	if what == 'v_bitrate_kbits': # video bitrate in kbit
		try:
			return int(get_stream(json, 'video')['bit_rate'])/1000
		except:
			return 99999999999

total_reduction = 0

for dirname, subname, filename in os.walk(input_path):
	for f in filename:
		if not f.lower().startswith('.') and f.lower().endswith(VALID_VIDEO_EXTENSIONS):

			# check if we should skip because we already processed it
			if '[x265-reenc]' in f: # bitrate checks would catch ourselves too, but just checking the filename is faster
				print('Skipping because it has [x265-reenc] in its filename:',f)
				continue

			fpath = os.path.abspath(os.path.join(dirname,f))
			#print(fpath)
			probe = json.loads(subprocess.check_output(['ffprobe', '-show_format', '-show_streams', '-loglevel', 'quiet', '-print_format', 'json', fpath]))

			# check if we should skip due to video properties
			if get_info(probe, 'v_bitrate_kbits') <= minimum_video_bitrate: # low bitrate
				print('Skipping because bitrate is too low:',f)
				continue
			if get_info(probe, 'height') <= minimum_video_height:
				print('Skipping because resolution is too low:',f)
				continue
			if get_info(probe, 'vcodec') == 'hevc':
				print('Skipping because its already hevc:',f)
				continue

			# verify target bitrate will be lower than source bitrate
			if get_info(probe, 'height') == 480 and get_info(probe, 'v_bitrate_kbits') <= target_480p:
				print('Skipping because source bitrate (' + str(get_info(probe, 'v_bitrate_kbits')) + ') is less than target bitrate (' + str(target_480p) + '):',f)
				continue
			elif get_info(probe, 'height') == 720 and get_info(probe, 'v_bitrate_kbits') <= target_720p:
				print('Skipping because source bitrate (' + str(get_info(probe, 'v_bitrate_kbits')) + ') is less than target bitrate (' + str(target_720p) + '):',f)
				continue
			elif get_info(probe, 'height') == 1080 and get_info(probe, 'v_bitrate_kbits') <= target_1080p:
				print('Skipping because source bitrate (' + str(get_info(probe, 'v_bitrate_kbits')) + ') is less than target bitrate (' + str(target_1080p) + '):',f)
				continue
			elif get_info(probe, 'height') == 2160 and get_info(probe, 'v_bitrate_kbits') <= target_2160p:
				print('Skipping because source bitrate (' + str(get_info(probe, 'v_bitrate_kbits')) + ') is less than target bitrate (' + str(target_2160p) + '):',f)
				continue

			tempname = 'reenc_temp_' + md5_string(fpath) + '.' + output_video_extension # file ffmpeg writes to 
			#print("tempname",tempname)
			basename = os.path.splitext(f)[0]
			clean_name = "".join([c for c in basename if c.isalpha() or c.isdigit() or c in VALID_FILENAME_SYMBOLS]).rstrip()
			outfile = os.path.abspath(os.path.join(dirname, clean_name + ' [x265-reenc].' + output_video_extension)) # actual resulting filename (and path)

			print('\nSource:',f)
			print('\tVideo:',get_info(probe,'vresolution'), str(get_info(probe,'vfps')) + 'fps', get_info(probe, 'vcodec'), str(round(get_info(probe, 'v_bitrate_kbits'),0)) + 'kbps')
			print('\tAudio:',get_info(probe, 'acodec'), str(get_info(probe,'achannels')) + 'ch', str(round(get_info(probe, 'a_bitrate_kbits'),0)) + 'kbps')
			print('\tDuration:',get_info(probe,'duration_HHMMSSXXX'))
			print('\tSize:',str(round(get_info(probe, 'sizeMB'),1)) + ' MB')

			size_before = get_info(probe, 'sizeMB')

			# prepare other-transcode command
			ot_cmd = [ot, '-n', fpath] # -n for dry-run so we can capture the command
			ot_cmd.extend( ['--target', '480p=' + str(target_480p)] ) # add the target bitrates
			ot_cmd.extend( ['--target', '720p=' + str(target_720p)] )
			ot_cmd.extend( ['--target', '1080p=' + str(target_1080p)] )
			ot_cmd.extend( ['--target', '2160p=' + str(target_2160p)] )
			additional = list(ot_settings.split(" "))
			ot_cmd.extend(additional)
			if output_video_extension == 'mp4' and '--mp4' not in ot_cmd:
				ot_cmd.append('--mp4')
			print(ot_cmd)
			
			# call other-transcode and mangle the resulting ffmpeg command
			s = subprocess.check_output(ot_cmd).decode('utf8')
			if s.startswith('ffmpeg'): # we capture the ffmpeg command so we can replace the output name
				#print('before:',s)
				if ' ' in f:
					#s = s.replace('"' + f + '"', tempname) # this doesnt work if output extension is different
					s = s.replace('"' + basename + '.' + output_video_extension + '"', tempname)
				elif ' ' not in f:
					# if no space is in filename then no "" are added so we remove the last word (original filename) and put in the tempname
					s = s.rsplit(' ', 1)[0] # removes last word
					s = s + ' ' + tempname # adds tempname back
				#print('after:',s)

			# actually transcode
			print('ffmpeg command:',s) # good for debugging
			subprocess.call(s, shell=True)

			# get new size reduction
			probe = json.loads(subprocess.check_output(['ffprobe', '-show_format', '-show_streams', '-loglevel', 'quiet', '-print_format', 'json', tempname]))
			size_after = get_info(probe, 'sizeMB')
			size_reduction = size_before - size_after
			print('New size:', round(size_after,1), 'MB (Before:', round(size_before,1), 'MB)')
			total_reduction += size_reduction

			# move/rename tempfile to final destination
			print('Moving result:', tempname, '-->', outfile)
			shutil.move(tempname, outfile)

			# check if srt exists and copy and maybe even delete it
			# TODO check for more languages instead of hardcoding the .swe.srt part... probably a regex like *.***.srt
			srt_path = os.path.abspath(os.path.join(dirname, basename + '.swe.srt'))
			if os.path.isfile(srt_path):
				new_srt_path = os.path.abspath(os.path.join(dirname, clean_name + ' [x265-reenc].swe.srt'))
				print('Copying SRT:', srt_path, '-->', new_srt_path)
				shutil.copy(srt_path, new_srt_path)
				if delete_original:
					print('Deleting original SRT:',srt_path)
					os.remove(srt_path)
			else:
				print('No SRT found.')

			# delete original file?
			if delete_original:
				print('Deleting original:',fpath)
				os.remove(fpath)

			print('Done with this video, saved', str(round(size_reduction,1)), 'MB (Total this session:',round(total_reduction,1),'MB)')
		else:
			print('Skipping because it doesnt have a video extension:', f)	

print('\nAll done! Total size reduction this session:',round(total_reduction,1),'MB')