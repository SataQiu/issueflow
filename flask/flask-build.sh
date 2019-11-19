#!/usr/bin/env bash
set -x
DEST="/tmp/flask"
rm -rf "$DEST"
mkdir -p "$DEST"

cp Dockerfile "$DEST"
cp gunicorn.conf.py "${DEST}/"
cp flask-entry.py "$DEST"
cp -Rf ../githubutil "$DEST"
cp ../config/workflow.yaml "$DEST/config.yaml"
cp flask-requirements.txt "$DEST/requirements.txt"

cd "$DEST"
find . -name __pycache__ -exec rm -Rf {} \;
find . -name *.pyc -exec rm -Rf {} \;
