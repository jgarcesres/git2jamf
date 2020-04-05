#!/bin/zsh
#by juan garces

#logfile="/Library/Logs/virtual_box_install_script.log"
loggedInUser=$( scutil <<< "show State:/Users/ConsoleUser" | awk -F': ' '/[[:space:]]+Name[[:space:]]:/ { if ( $2 != "loginwindow" ) { print $2 }}' )

#grab the latest stable vesrsion of virtual box
vb_latest=`curl -s --request GET \
    --url "https://download.virtualbox.org/virtualbox/LATEST-STABLE.TXT" \
    --header "accept: application/json" \
    --header "content-type: application/json"`
echo "--"
echo "`date`: latest stable version is $vb_latest" 
#find the dmg for the given version of virtual box
vb_list=`curl -s --request GET \
--url "https://download.virtualbox.org/virtualbox/$vb_latest/" \
--header "accept: application/json" \
--header "content-type: application/json"`
echo "`date`: grabbing the name of the macOS dmg from the $vb_latest folder" 
#this is the latest stable version
mac_dmg=`echo $vb_list | grep "OSX" | awk -F'>|<' '{print $3}'`
echo "`date`: macos DMG is: $mac_dmg" 

url="https://download.virtualbox.org/virtualbox/$vb_latest/$mac_dmg"
echo "`date`: grabbing the file from $url" 
dmgfile="/tmp/$mac_dmg"
sudo -u "$loggedInUser" curl -s -o $dmgfile --url $url
echo "--"
echo "`date`: grabbing checksum"
url="https://download.virtualbox.org/virtualbox/$vb_latest/MD5SUMS"
md5_list=`curl -s --request GET \
    --url $url \
    --header "accept: application/json" \
    --header "content-type: application/json"`
web_md5=`echo $md5_list | grep "OSX" | awk '{print $1}'`
echo "`date`: md5 from the website is $web_md5"
local_md5=`md5 $dmgfile | awk '{print $4}'`
echo "`date`: md5 from the downloaded file is $local_md5"
if [ $web_md5 != $local_md5 ]; then
    echo "`date`: checksum is different, abort, abort abort!"
    exit 1
fi
echo "`date`: checksum checks's out, continuing"
echo "--" 
echo "`date`: Mounting installer disk image." 
/usr/bin/hdiutil attach $dmgfile -nobrowse -quiet

echo "`date`: Installing..." 
installer -pkg "/Volumes/VirtualBox/VirtualBox.pkg" -target / 

echo "`date`: Unmounting installer disk image." 
/usr/bin/hdiutil detach "$(/bin/df | /usr/bin/grep "VirtualBox" | awk '{print $1}')" -quiet

echo "`date`: Deleting disk image." 
/bin/rm "${dmgfile}"


exit 0