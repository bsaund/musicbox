# musicbox
Instructions and code for my raspberry pi music box

This is still an early work in progress


Notes on setting up mopidy on my raspberry pi to work as a music player
1. Installed raspian
set up VNC, ssh, bluetooth audio
2. Installed mopidy: https://docs.mopidy.com/en/latest/installation/debian/#debian-install
Set up for systemctl
Update mopidy config file
`sudo addusr mopidy` to audio and bluetooth (and video?) groups
3. Make pulseaudio play nicely: https://docs.mopidy.com/en/latest/running/service/?highlight=pulseaudio#system-service-and-pulseaudio
Add `load-module module-switch-on-connect` to `/etc/pulse/default.pa` to autoconnect to bluetooth as the speaker turns off and on:
https://github.com/manjaro/packages-extra/issues/64 
4. TODO: Write python script to respond to mouse events
https://thehackerdiary.wordpress.com/2017/04/21/exploring-devinput-1/
https://stackoverflow.com/questions/54745576/detecting-the-buttons-on-a-bluetooth-remote-hid-over-gatt
Basic script is written. 
Now need to integrate with scanner
Need to handle bluetooth connect/disconnect
5. Install mopidy IRIS from source: 
https://github.com/jaedb/Iris

