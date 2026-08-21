#!/bin/bash
export DISPLAY=:99
cd "/home/serpentarius/Repos/ORA-widget/engine/openra-cnc/usr/lib/openra"
export LD_LIBRARY_PATH="/home/serpentarius/Repos/ORA-widget/engine/openra-cnc/usr/lib/openra"
exec /home/serpentarius/Repos/ORA-widget/engine/openra-cnc/usr/bin/openra-cnc Game.Mod=cnc Sound.Device=null Game.ViewportEdgeScroll=false Graphics.Mode=Windowed Graphics.WindowedSize=1280,720 Launch.Map=35c76d9b513670d24a60d1d2db76232fc7ca19db
