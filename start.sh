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

  # Watch for bot process termination and override timer if necessary
  while true; do
    # Check if the bot process is still running
    if ! ps -p $BOT_PID > /dev/null; then
      echo "Bot process ended. Restarting immediately."
      break
    fi

    # If less than 20 seconds remain, start countdown
    if [ $wait_seconds -le 20 ]; then
      echo "Restart time is near! Countdown: 20 seconds remaining."
      for ((i=20; i>=0; i--)); do
        echo "Restarting in $i seconds..."
        sleep 1
      done
      break
    else
      # Sleep until 20 seconds before restart time
      sleep $((wait_seconds - 20))
      echo "Restart time is near! Countdown: 20 seconds remaining."
      for ((i=20; i>=0; i--)); do
        echo "Restarting in $i seconds..."
        sleep 1
      done
      break
    fi
  done

  # Stop the bot process if it's still running
  kill $BOT_PID
done
