#!/bin/bash
set -e

source venv/bin/activate

pyinstaller --onefile --noconsole --name "FilmDosimetryGUI" main.py

# Clean PyInstaller artifacts
rm -rf build FilmDosimetryGUI.spec
mv dist/FilmDosimetryGUI ./
rm -rf dist

# Create AppImage directory structure
mkdir -p FilmDosimetryGUI.AppDir/usr/bin
cp FilmDosimetryGUI FilmDosimetryGUI.AppDir/usr/bin/

# Create desktop entry
cat > FilmDosimetryGUI.AppDir/FilmDosimetryGUI.desktop << EOF
[Desktop Entry]
Type=Application
Name=FilmDosimetryGUI
Exec=FilmDosimetryGUI
Icon=icon
Categories=Science;
EOF

# Copy icon if available
if [ -f "_icons/icon.png" ]; then
    cp _icons/icon.png FilmDosimetryGUI.AppDir/icon.png
elif [ -f "_icons/icon.ico" ]; then
    cp _icons/icon.ico FilmDosimetryGUI.AppDir/icon.ico
fi

# Create AppRun with correct working directory
cat > FilmDosimetryGUI.AppDir/AppRun << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}

# Get AppImage location directory
APPIMAGE_PATH="$(readlink -f "${ARGV0}")"
if [ -n "$APPIMAGE_PATH" ]; then
    APPIMAGE_DIR="$(dirname "$APPIMAGE_PATH")"
else
    APPIMAGE_DIR="$(pwd)"
fi

export PATH="${HERE}/usr/bin/:${PATH}"
cd "$APPIMAGE_DIR"
exec "${HERE}/usr/bin/FilmDosimetryGUI" "$@"
EOF
chmod +x FilmDosimetryGUI.AppDir/AppRun

# Download appimagetool if needed
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x appimagetool-x86_64.AppImage
fi

# Build AppImage
ARCH=x86_64 ./appimagetool-x86_64.AppImage FilmDosimetryGUI.AppDir FilmDosimetryGUI.AppImage

# Clean up
rm -rf FilmDosimetryGUI.AppDir FilmDosimetryGUI appimagetool-x86_64.AppImage

echo "Build completed: FilmDosimetryGUI.AppImage"
