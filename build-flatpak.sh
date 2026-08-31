#!/bin/sh
set -eu

python3 scripts/validate.py

flatpak run org.flatpak.Builder \
  --user \
  --install \
  --force-clean \
  build-dir \
  io.github.laurentiustaicu.World3Empirical.yml
