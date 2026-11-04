#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if [ ! -f .venv/.haven-ready ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
  touch .venv/.haven-ready
fi
exec .venv/bin/python run.py
