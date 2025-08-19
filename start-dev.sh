#!/bin/sh
export ENV=development
export SERVER_VOLUME=.:/app
docker compose up --build