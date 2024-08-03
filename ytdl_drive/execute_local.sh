youtube-dl -x -i --yes-playlist --audio-format mp3 -a url_list.txt
mkdir -p files
mv *.mp3 files/
python sync_drive.py