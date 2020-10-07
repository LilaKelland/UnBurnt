#!/bin/bash

set -m
python UnBurntAPI.py &
python UnBurnt.py

fg %1