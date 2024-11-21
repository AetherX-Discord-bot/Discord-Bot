#!/bin/bash

# Run other script
node other/note.js

# Wait for 5 seconds
sleep 5

while true; do
  echo "Starting bot..."

  # Start bot in the background
  node bot.js &
  BOT_PID=$!

  # Calculate time until the next restart (12 PM or 12 AM)
  now=$(date +%s)
  next_noon=$(date -d '12:00' +%s)
  next_midnight=$(date -d '00:00 tomorrow' +%s)
  if [ $now -lt $next_noon ]; then
    wait_seconds=$((next_noon - now))
  else
    wait_seconds=$((next_midnight - now))
  fi

  # Wait until the next restart time
  sleep $wait_seconds

  # Stop the bot process
  kill $BOT_PID
done
