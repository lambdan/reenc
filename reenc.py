import sys, os, shutil, re
import subprocess
import json
import hashlib
import datetime
from subprocess import DEVNULL
from curses import ascii # pip3 install windows-curses

# settings !

delete_original = False # if True, source files will be deleted! dangerous!!!
input_path = 'Z:/Video/' # folder with videos to batch through (also goes through subfolders)
output_path = 'same' # converted videos saved here. set to "same" to put them in the same folder as input.
ignored_folders = ['_Incoming'] # ignore these folders in the input_path
minimum_video_bitrate = 4000 # videos with lower/equal bitrate to this will be skipped (kbps)
minimum_video_height = 720 # videos with lower/equal resolution to this will be skipped
ot = os.path.abspath(os.path.join('C:/Ruby27-x64/bin', 'other-transcode.bat')) # path to other-transcode.bat (Windows is great, isn't it).. on unix i think you can just change this line to ` ot = 'other-transcode' ` ?
ot_settings = '--crop auto --nvenc --10-bit --hevc' # these are passed to other-transcode
output_video_extension = 'mp4' # mp4 or mkv
subtitle_languages = ["swe", "eng", "sv", "en"]
skipped_db = 'reenc_skipped.txt'

# target video bitrates in kbps
target_480p = 500
target_720p = 1000
target_1080p = 2500
target_2160p = 7000

VALID_VIDEO_EXTENSIONS = ('mp4','wmv','avi','flv','m4v','mkv','mpg')
VALID_FILENAME_SYMBOLS = [',', '.', '[', ']', ' ', '(', ')', '-', '_']

# end of settings

# show settings
print ('Folder to process:', input_path)
print ('Output folder:', output_path)
print ('Delete original:', delete_original)
print ('Minimum bitrate:', minimum_video_bitrate)
print ('Minimum video resolution:', minimum_video_height)
print ('Additional other-transcode settings:', ot_settings)
print ('Video extension for output:', output_video_extension)
print ('Subtitles to copy:', subtitle_languages)
print ('Skip db:', skipped_db)
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

def xml_clean(text): # https://stackoverflow.com/a/20819845
	return str(''.join(ascii.isprint(c) and c or '' for c in text)) 

def skip_file(fp, reason):
	# fp = full file path, reason = reason
	with open(skipped_db, 'a') as sf:
		sf.write(str(xml_clean(fp)) + ': ' + reason + ' | ' + md5_string(fpath) + '\n')

def get_info(json, ot_scan, what):
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
		for l in ot_scan.split('\n'):
			if not 'fps' in l and 'Kbps' in l: # find audio line
				s = l.split('/')
				for a in s:
					if 'Kbps' in a:
						only_numbers = int(re.sub("[^0-9]", "", a)) # https://stackoverflow.com/a/1249424
						return only_numbers
						# TODO backup audio bitrate like video bitrate

	if what == 'width': # 1920 etc.
		return int(get_stream(json, 'video')['width'])

	if what == 'height': # 1080 etc.
		return int(get_stream(json, 'video')['height'])

	if what == 'v_bitrate_kbits': # video bitrate in kbit
		for l in ot_scan.split('\n'):
			if "fps" in l and "Kbps" in l: # find video line
				s = l.split('/')
				for a in s:
					if 'Kbps' in a:
						only_numbers = int(re.sub("[^0-9]", "", a)) # https://stackoverflow.com/a/1249424
						return only_numbers
			elif "fps" in l and not "Kbps" in l: # figure bitrate dirty way by dividing size with length
				secs = float(json['format']['duration'])
				size = int(json['format']['size'])
				result = ((size/secs)*8)/1000 # (MB/secs) * 8 to get bits, then /1000 to get Kbit
				result -= get_info(json, ot_scan, 'a_bitrate_kbits') # remove audio bitrate
				return int(result)

total_reduction = 0
skipped_files = []

# Read previously skipped files
if os.path.isfile(skipped_db):
	print("Reading skipped files from",skipped_db)
	print("If you want to start clean just remove the file:", skipped_db)
	with open(skipped_db) as f:
		lines = f.readlines()
	for line in lines:
		skipped_files.append(line.rstrip().split(' | ')[1])
	print("Read", len(skipped_files),"skipped files from",skipped_db)

for dirpath, dirnames, filenames in os.walk(input_path):
	# remove ignored_folders # https://stackoverflow.com/a/38928455
	for ig in ignored_folders:
		if ig in dirnames:
			#print("removing folder from walk",ig)
			dirnames.remove(ig)
	for f in filenames:
		fpath = os.path.abspath(os.path.join(dirpath,f)) # input file path
		if md5_string(fpath) in skipped_files:
			#print("skipping becasue it was in skip db",f)
			continue
		if not f.lower().startswith('.') and f.lower().endswith(VALID_VIDEO_EXTENSIONS):

			# check if we should skip because we already processed it
			if '[x265-reenc]' in f: # bitrate checks would catch ourselves too, but just checking the filename is faster
				print('Skipping because it has [x265-reenc] in its filename:',f)
				skip_file(fpath,'x265-reenc in filename')
				continue

			# decide output path
			if output_path.lower() == "same":
				outpath = dirpath # same folder as input
			else:
				outpath = os.path.abspath(output_path)
				if not os.path.isdir(outpath):
					os.makedirs(outpath)

			# use ffprobe and other_transcode's --scan to get info about video
			probe = json.loads(subprocess.check_output(['ffprobe', '-show_format', '-show_streams', '-loglevel', 'quiet', '-print_format', 'json', fpath]))
			ot_scan = subprocess.check_output([ot, '--scan', fpath],stderr=DEVNULL).decode() # removing stderr hides "Verying ffmpeg availaility..." messages from other-transcode

			# check if we should skip due to video properties
			if get_info(probe, ot_scan, 'height') <= minimum_video_height:
				print('Skipping because resolution is too low:',f, '(' + str(get_info(probe, ot_scan, 'height')) + 'p <= ' + str(minimum_video_height) + 'p)')
				skip_file(fpath,'resolution too low')
				continue
			if get_info(probe, ot_scan, 'v_bitrate_kbits') <= minimum_video_bitrate: # low bitrate
				print('Skipping because bitrate is too low:',f, '(' + str(get_info(probe, ot_scan, 'v_bitrate_kbits')) + ' <= ' + str(minimum_video_bitrate) + ')')
				skip_file(fpath,'bitrate too low')
				continue
			if get_info(probe, ot_scan, 'vcodec') == 'hevc':
				print('Skipping because its already hevc:',f)
				skip_file(fpath,'already hevc')
				continue

			# verify target bitrate will be lower than source bitrate
			if get_info(probe, ot_scan, 'height') == 480 and get_info(probe, ot_scan, 'v_bitrate_kbits') <= target_480p:
				print('Skipping because source bitrate (' + str(get_info(probe, ot_scan, 'v_bitrate_kbits')) + ') is less than target bitrate (' + str(target_480p) + '):',f)
				skip_file(fpath,'source bitrate less than target (480p)')
				continue
			elif get_info(probe, ot_scan, 'height') == 720 and get_info(probe, ot_scan, 'v_bitrate_kbits') <= target_720p:
				print('Skipping because source bitrate (' + str(get_info(probe, ot_scan, 'v_bitrate_kbits')) + ') is less than target bitrate (' + str(target_720p) + '):',f)
				skip_file(fpath,'source bitrate less than target (720p)')
				continue
			elif get_info(probe, ot_scan, 'height') == 1080 and get_info(probe, ot_scan, 'v_bitrate_kbits') <= target_1080p:
				print('Skipping because source bitrate (' + str(get_info(probe, ot_scan, 'v_bitrate_kbits')) + ') is less than target bitrate (' + str(target_1080p) + '):',f)
				skip_file(fpath,'source bitrate less than target (1080p)')
				continue
			elif get_info(probe, ot_scan, 'height') == 2160 and get_info(probe, ot_scan, 'v_bitrate_kbits') <= target_2160p:
				print('Skipping because source bitrate (' + str(get_info(probe, ot_scan, 'v_bitrate_kbits')) + ') is less than target bitrate (' + str(target_2160p) + '):',f)
				skip_file(fpath,'source bitrate less than target (2160p)')
				continue

			tempname = 'reenc_temp_' + md5_string(fpath) + '.' + output_video_extension # file ffmpeg writes to 
			#print("tempname",tempname)
			# check for old tempfile and remove it
			if os.path.isfile(tempname):
				print('Removing leftover tempfile...')
				os.remove(tempname)


			basename = os.path.splitext(f)[0]
			clean_name = "".join([c for c in basename if c.isalpha() or c.isdigit() or c in VALID_FILENAME_SYMBOLS]).rstrip()
			outfile = os.path.abspath(os.path.join(outpath, clean_name + ' [x265-reenc].' + output_video_extension)) # actual resulting filename (and path)

			# check if outfile already exist, skip if so
			if os.path.isfile(outfile):
				print("Skipping",f,"because output already exists:",outfile)
				# dont check if in skipped_files here because maybe user wants to re-encode
				continue

			print('\nSource:',f)
			print('\tVideo:',get_info(probe,ot_scan, 'vresolution'), str(get_info(probe,ot_scan, 'vfps')) + 'fps', get_info(probe, ot_scan, 'vcodec'), str(round(get_info(probe,ot_scan,  'v_bitrate_kbits'),0)) + 'kbps')
			print('\tAudio:',get_info(probe,ot_scan,  'acodec'), str(get_info(probe,ot_scan, 'achannels')) + 'ch', str(round(get_info(probe, ot_scan, 'a_bitrate_kbits'),0)) + 'kbps')
			print('\tDuration:',get_info(probe,ot_scan, 'duration_HHMMSSXXX'))
			print('\tSize:',str(round(get_info(probe,ot_scan,  'sizeMB'),1)) + ' MB')

			size_before = get_info(probe, ot_scan, 'sizeMB')

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
			#print(ot_cmd)
			
			# call other-transcode and mangle the resulting ffmpeg command
			s = subprocess.check_output(ot_cmd,stderr=DEVNULL).decode('utf8')
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
			ot_scan = subprocess.check_output([ot, '--scan', tempname],stderr=DEVNULL).decode()
			size_after = get_info(probe,ot_scan,  'sizeMB')
			size_reduction = size_before - size_after
			print('New size:', round(size_after,1), 'MB (Before:', round(size_before,1), 'MB)')
			total_reduction += size_reduction

			# move/rename tempfile to final destination
			print('Moving result:', tempname, '-->', outfile)
			shutil.move(tempname, outfile)

			# check if srt exists and copy and maybe even delete it
			# TODO check for more languages instead of hardcoding the .swe.srt part... probably a regex like *.***.srt
			for lang in subtitle_languages:
				srt_path = os.path.abspath(os.path.join(dirpath, basename + '.' + lang + '.srt'))
				if os.path.isfile(srt_path):
					new_srt_path = os.path.abspath(os.path.join(outpath, clean_name + ' [x265-reenc].' + lang + '.srt'))
					print('Copying SRT:', srt_path, '-->', new_srt_path)
					shutil.copy(srt_path, new_srt_path)
					if delete_original:
						print('Deleting original SRT:',srt_path)
						os.remove(srt_path)
				else:
					print('No SRT for ' + lang + ' found.')

			# delete original file?
			if delete_original:
				print('Deleting original:',fpath)
				os.remove(fpath)

			print('Done with this video, saved', str(round(size_reduction,1)), 'MB (Total this session:',round(total_reduction,1),'MB)')
			# add encoded video to future skips
			skip_file(fpath,'encoded by reenc ' + str(datetime.datetime.now()))
		else:
			print('Skipping because it doesnt have a video extension:', f)
			skip_file(fpath, 'no video extension')

print('\nDone with all transcoding! Total size reduction this session:',round(total_reduction,1),'MB')