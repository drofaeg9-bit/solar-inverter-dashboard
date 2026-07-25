#!/usr/bin/env bash
set -euo pipefail

readonly IMAGE="/mnt/c/Users/oleks/Desktop/solar-assistant-vm/2024-08-14-solar-assistant.rpi64.img"
readonly SERIAL_LOG="/mnt/c/Users/oleks/Desktop/solar-assistant-vm/solarassistant-serial.log"

echo "Starting Solar Assistant VM..."
qemu-system-aarch64 \
    -name SolarAssistant_OS_WSL \
    -machine raspi4b \
    -drive "file=${IMAGE},format=raw,if=sd" \
    -netdev user,id=solarassistant_net,hostfwd=tcp::8080-:80 \
    -device usb-net,netdev=solarassistant_net \
    -serial "file:${SERIAL_LOG}" \
    -nographic \
    -no-reboot
