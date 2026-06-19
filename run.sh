#!/usr/bin/env bash
# Avvio dell'app DOPAMINIC
cd "$(dirname "$0")"
if [ -x env/bin/python ]; then
    env/bin/python app.py
else
    python app.py
fi
