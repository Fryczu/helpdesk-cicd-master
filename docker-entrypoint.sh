#!/bin/sh
set -eu

python init_db.py
exec "$@"
