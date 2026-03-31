#!/usr/bin/env bash
set -e

pyinstaller \
    --onefile \
    --name podfather \
    podfather.py

echo "Binary: dist/podfather"
