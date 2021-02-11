#!/usr/bin/env python3

"""
This launches albums on mopidy

still a work in progress
"""

from mopidy_json_client import MopidyClient
import pathlib
import urllib.parse

TESTING = False

if TESTING:
    BASE_FP = "/home/bsaund/Dropbox/Music/"
    mp = MopidyClient(ws_url='ws://192.168.1.54:6680/mopidy/ws')
else:
    BASE_FP = "/home/pi/Dropbox/Music"
    mp = MopidyClient()


def add_all_songs_from_folder(folder):
    d = pathlib.Path(BASE_FP) / folder
    uris = sorted(['file://' + urllib.parse.quote(fp.as_posix()) for fp in d.glob('[!._]*.mp3')])
    # uris = [urllib.parse.quote(a) for a in uris]
    mp.tracklist.mopidy_request('core.tracklist.add', uris=uris)

    # pathilb.Path()


# current_tracks = mp.tracklist.get_tracks()
# print(current_tracks)
# print(f"There are currently {len(current_tracks)} Tracks")
mp.tracklist.clear()
print(f"After clearing, there are {len(mp.tracklist.get_tracks())} tracks")
# mp.tracklist.mopidy_request('core.tracklist.add', uris=[
#     'file:///home/pi/Music/Videogame/Final%20Fantasy%20Concert%2020020220/Dear%20Friends%20%28FFV%29.mp3'])
# mp.tracklist.mopidy_request('core.tracklist.add', uris=[
#     'file:///home/pi/Music/Test/Devorak/Slavonic%20Dances%20Op.46%20and%20Op.%2072%20-%20Cleveland%2C%20Szell/01%20Op.%2046%20%231%20In%20C%20Major.mp3'])

# mp.tracklist.mopidy_request('core.tracklist.add', uris=[
#     "file:///home/pi/Music/Test/Devorak/01%20Op.%2046%20%231%20In%20C%20Major.mp3"
# ])
# add_all_songs_from_folder('Test/Devorak')

# add_all_songs_from_folder('Videogame/Final Fantasy Concert 20020220')
# add_all_songs_from_folder('Test')
add_all_songs_from_folder('Classical/Devorak/Slavonic Dances Op.46 and Op. 72 - Cleveland, Szell')
# add_all_songs_from_folder("Pop/Beatles/Sgt. Pepper's Lonely Hearts Club Bandy")
mp.playback.play()

current_tracks = mp.tracklist.get_tracks()
print(current_tracks)
print(f"After update there are {len(current_tracks)}")

