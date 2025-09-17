#!/usr/bin/env bash
set -euo pipefail

# Launch producers and actuators, then manager and GUI.
# Requires: Python 3 with dependencies from requirements.txt

# ----------------------------
# Configuration (tweak here)
# ----------------------------

# Level emulators (name units place update_seconds)
# Units are not used for levels; keep as "N"
FOOD_NAME="FoodTank-1";  FOOD_UNITS="N"; FOOD_PLACE="food-1";  FOOD_RATE=5
WATER_NAME="WaterTank-1"; WATER_UNITS="N"; WATER_PLACE="water-1"; WATER_RATE=5
FOOD_TRAY_NAME="FoodTray-1"; FOOD_TRAY_UNITS="N"; FOOD_TRAY_PLACE="foodtray-1"; FOOD_TRAY_RATE=5
WATER_TRAY_NAME="WaterTray-1"; WATER_TRAY_UNITS="N"; WATER_TRAY_PLACE="watertray-1"; WATER_TRAY_RATE=5

# Feeder device emulator target name (topic suffix)
FEEDER_DEVICE="feeder"

# Tip: Override MQTT broker via env before running, e.g.:
#   export SMARTPETFEEDER_BROKER_HOST=broker.hivemq.com
#   export SMARTPETFEEDER_BROKER_PORT=1883

# Track background PIDs for clean shutdown
PIDS=()

# Env sensor emulators removed for a focused Pet Feeder demo
# Start FoodLevel emulator (publishes Level: X% to pr/PetFeeder/${FOOD_PLACE}/pub)
python3 -m smart_pet_feeder.tank_tray_emulator "$FOOD_NAME" "$FOOD_UNITS" "$FOOD_PLACE" "$FOOD_RATE" &
PIDS+=($!)
sleep 1
# Start WaterLevel emulator (publishes Level: X% to pr/PetFeeder/${WATER_PLACE}/pub)
python3 -m smart_pet_feeder.tank_tray_emulator "$WATER_NAME" "$WATER_UNITS" "$WATER_PLACE" "$WATER_RATE" &
PIDS+=($!)
sleep 1
python3 -m smart_pet_feeder.tank_tray_emulator "$FOOD_TRAY_NAME" "$FOOD_TRAY_UNITS" "$FOOD_TRAY_PLACE" "$FOOD_TRAY_RATE" &
PIDS+=($!)
sleep 1
python3 -m smart_pet_feeder.tank_tray_emulator "$WATER_TRAY_NAME" "$WATER_TRAY_UNITS" "$WATER_TRAY_PLACE" "$WATER_TRAY_RATE" &
PIDS+=($!)
sleep 1

# Actuator device emulator (feeder)
# Subscribes to pr/PetFeeder/${FEEDER_DEVICE}/sub; publishes status to /pubsmar
python3 -m smart_pet_feeder.feeder_emulator "$FEEDER_DEVICE" &
PIDS+=($!)
sleep 1

# Relay is handled within the feeder emulator/UI; no separate process needed

# Manager and GUI
# Manager subscribes to pr/PetFeeder/#, writes to SQLite, emits alarms
python3 -m smart_pet_feeder.manager &
PIDS+=($!)
sleep 3
# GUI subscribes to updates and lets you send commands
python3 -m smart_pet_feeder.app_gui &
PIDS+=($!)

cleanup() {
  echo "Stopping Smart Pet Feeder processes..."
  # best-effort stop
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  # give them a moment to exit gracefully
  sleep 1
  for pid in "${PIDS[@]}"; do
    kill -9 "$pid" 2>/dev/null || true
  done
}

trap cleanup INT TERM EXIT

echo "Started emulators, manager, and GUI. Press Ctrl+C to stop."

# keep script alive to handle Ctrl+C and cleanup
wait
