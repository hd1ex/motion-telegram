#!/usr/bin/env sh
env $(cat .env | xargs) python motion-telegram.py
