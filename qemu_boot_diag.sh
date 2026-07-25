#!/usr/bin/env bash
set -euo pipefail

perl -0pi -e 's/ quiet//g' /mnt/solarassistant_boot/cmdline.txt

if ! grep -q "Codex QEMU diagnostics" /mnt/solarassistant_boot/config.txt; then
    cat >> /mnt/solarassistant_boot/config.txt <<'EOF'

# Codex QEMU diagnostics
force_hdmi_hotplug=1
hdmi_group=2
hdmi_mode=82
enable_uart=1
uart_2ndstage=1
EOF
fi

sync
