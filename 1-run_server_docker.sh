#!/bin/bash

sudo docker run --rm -it --network='host' -v "$PWD":/app -w /app python:3.7.1-alpine python /app/start_server.py
