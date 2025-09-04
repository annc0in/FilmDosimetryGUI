#!/bin/bash

# Remove all Qt-related environment variables from PyQt6
unset QT_PLUGIN_PATH
unset QT_QPA_PLATFORM_PLUGIN_PATH
unset DYLD_LIBRARY_PATH
unset DYLD_FRAMEWORK_PATH
unset QML_IMPORT_PATH
unset QML2_IMPORT_PATH

# Set clean PATH
export PATH="/usr/local/bin:/usr/bin:/bin:/sbin"

# Set Octave environment
export OCTAVE_GUI_MODE=1

# Change to working directory
cd "$1"

if [ $# -eq 1 ]; then
    # for processing_screen (no gnuplot needed)
    exec /usr/local/bin/octave --no-gui --eval "pkg load io image; Check_calibration_XD_add_films();"
else
    # for progress_screen (gnuplot needed)
    # Set proper locale and encoding for gnuplot
    export LC_ALL=en_US.UTF-8
    export LANG=en_US.UTF-8
    export LC_CTYPE=en_US.UTF-8
    
    # Set gnuplot environment
    export GNUTERM=qt
    export GNUPLOT_DRIVER_DIR=/usr/local/libexec/gnuplot/5.4
    
    exec /usr/local/bin/octave --no-gui --no-line-editing --eval "$2"
fi