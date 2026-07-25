#!/usr/bin/env bash
set -euo pipefail

readonly IMAGE="/mnt/c/Users/oleks/Desktop/solar-assistant-vm/2024-08-14-solar-assistant.rpi64.img"
readonly SERVICE="solarassistant-vm.service"
readonly SERIAL_LOG="/mnt/c/Users/oleks/Desktop/solar-assistant-vm/solarassistant-serial.log"

if systemctl --user is-active --quiet "${SERVICE}"; then
    echo "SolarAssistant VM is already running."
    systemctl --user --no-pager --full status "${SERVICE}"
    exit 0
fi

systemd-run --user \
    --unit="${SERVICE%.service}" \
    --property=Environment=DISPLAY="${DISPLAY:-:0}" \
    --property=Environment=WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" \
    --property=Environment=XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
    qemu-system-aarch64 \
    -name SolarAssistant_OS_WSL \
    -machine raspi4b \
    -drive "file=${IMAGE},format=raw,if=sd" \
    -device usb-kbd \
    -device usb-mouse \
    -netdev user,id=solarassistant_net,hostfwd=tcp:127.0.0.1:8080-:80 \
    -device usb-net,netdev=solarassistant_net \
    -serial "file:${SERIAL_LOG}" \
    -display gtk \
    -no-reboot

sleep 2

if systemctl --user is-active --quiet "${SERVICE}"; then
    echo "SolarAssistant VM started."
    systemctl --user --no-pager --full status "${SERVICE}"
else
    echo "SolarAssistant VM failed to start."
    journalctl --user --unit="${SERVICE}" --no-pager --lines=30
    exit 1
fi
