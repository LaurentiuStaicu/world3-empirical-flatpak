#!/bin/sh
set -eu

python3 scripts/validate.py
python3 -m unittest discover -s tests

flatpak run org.flatpak.Builder \
  --user \
  --install \
  --force-clean \
  build-dir \
  io.github.laurentiustaicu.World3Empirical.yml
