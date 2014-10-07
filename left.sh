#!/bin/bash
#
# Positions other windows to be the complement of right.sh.

window=`xdotool getactivewindow`
wmctrl -i -r $window -e 0,0,0,720,743
