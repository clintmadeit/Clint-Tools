#!/bin/sh

# Remove some brew dependencies to test that Pyinstaller linkage is
# working as expected

brew uninstall -y portaudio portmidi

open -b io.github.clintmadeit

brew install -y portaudio portmidi

