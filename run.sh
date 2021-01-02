#!/bin/bash

set -m
python3.7m UnBurntAPI.py &
python3.7m UnBurnt.py

fg %1
