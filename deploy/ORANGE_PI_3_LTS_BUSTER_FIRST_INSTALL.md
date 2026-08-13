# First installation: Orange Pi 3 LTS with Debian Buster 2.2.2

This guide installs the Solar Inverter Dashboard on a new Orange Pi 3 LTS using the supplied `lts_2.2.2_debian_buster_desktop_linux5.10.75.7z` image. It uses a microSD card and leaves eMMC untouched. After the first installation, use [ORANGE_PI_DEPLOYMENT.md](ORANGE_PI_DEPLOYMENT.md) for normal dashboard updates.

> [!WARNING]
> Debian 10 (Buster) reached end of LTS on 30 June 2024 and its packages are archived. Keep this device on a trusted LAN or behind Tailscale; do not forward dashboard port 8080 from the router. Use a current supported Orange Pi image instead when the specified Buster image is not a hard requirement.

## What you need

- Orange Pi 3 LTS, its correct power supply, and a network connection. Wired Ethernet is strongly recommended for the first setup.
- A good-quality microSD card of at least 16 GB and a card reader.
- The supplied `lts_2.2.2_debian_buster_desktop_linux5.10.75.7z` file.
- A monitor and keyboard for the first boot, or a way to discover the device IP address on the router.
- The USB-to-RS-232 adapter and inverter only when the operating system setup is complete.
- A development PC with this repository and an SSH/SCP client.

Do not power the board from an under-rated phone charger. An unstable supply can corrupt the card while the dashboard writes its SQLite history.

## 1. Flash the supplied operating-system image

On Windows, install [7-Zip](https://www.7-zip.org/) and [balenaEtcher](https://etcher.balena.io/).

1. Right-click `lts_2.2.2_debian_buster_desktop_linux5.10.75.7z` and choose **7-Zip → Extract Here**. This must produce an `.img` file. Do not flash the `.7z` archive itself.
2. Insert the microSD card, start balenaEtcher, choose the extracted `.img`, select the microSD card, and click **Flash**. Check the selected drive carefully: flashing erases that drive.
3. Eject the card after Etcher's validation completes, insert it into the Orange Pi, connect Ethernet, monitor, keyboard, and power.
4. Wait for the desktop login screen. Use the credentials included with the image download or its accompanying readme. Do not assume internet posts about default credentials apply to this image.
5. Complete any first-boot password-change prompt. Create a normal administrative user if the image requires it, then record that username as `ORANGE_PI_USER` for the commands below.

The official [Orange Pi 3 LTS resource page](https://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/service-and-support/Orange-pi-3-LTS.html) remains the source for board manuals and images.

## 2. Complete the first boot

Open a terminal on the Orange Pi and run the following read-only checks:

```bash
uname -a
cat /etc/os-release
hostnamectl
ip -brief address
```

Confirm the output identifies the Orange Pi image, Debian Buster, and a `5.10.75` kernel. Set a clear host name and time zone, replacing the examples with your own values:

```bash
sudo hostnamectl set-hostname solar-inverter
sudo timedatectl set-timezone Europe/Paris
sudo timedatectl set-ntp true
hostname -I
```

Use the IP address printed by `hostname -I` to connect from the development PC:

```powershell
ssh ORANGE_PI_USER@ORANGE_PI_IP
```

Accept the host key only after comparing the displayed fingerprint with the one shown on the Orange Pi console. From this point onward, run the remaining commands over SSH unless a command says otherwise.

## 3. Make APT work with the archived Buster repositories

The normal Buster mirrors and security repository no longer carry current indexes. Debian documents Buster as an archived release, so first save the image's original repository configuration:

```bash
sudo cp -a /etc/apt/sources.list /etc/apt/sources.list.image-original
sudo mkdir -p /etc/apt/sources.list.d/image-original
sudo cp -a /etc/apt/sources.list.d/. /etc/apt/sources.list.d/image-original/ 2>/dev/null || true
```

Open `/etc/apt/sources.list` with `sudoedit` and replace its contents with exactly:

```text
deb http://archive.debian.org/debian buster main contrib non-free
deb http://archive.debian.org/debian-security buster/updates main contrib non-free
```

Then disable every active image-vendor entry that points to an unavailable mirror. Inspect them first:

```bash
grep -R --line-number --no-messages '^deb ' /etc/apt/sources.list /etc/apt/sources.list.d
```

For each failing `.list` file outside `image-original`, open it with `sudoedit` and comment out its `deb` lines. Do not delete the saved copy. Finally create `/etc/apt/apt.conf.d/99buster-archive` with this one line:

```text
Acquire::Check-Valid-Until "false";
```

Refresh the package lists and install the base tools:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git python3 python3-venv tzdata \
  build-essential cmake pkg-config libtool autoconf automake libmodbus-dev
python3 --version
```

If `apt-get update` still reports an expired Release file, confirm that `99buster-archive` contains the line above and that there are no unedited Buster mirror entries. Do not use `--allow-unauthenticated`.

## 4. Install `mbpoll` from source

`mbpoll` was first packaged for Debian Bullseye, not Buster. Build it from its upstream source on this Buster image instead. The dashboard calls this command to read Modbus registers.

```bash
cd /tmp
git clone --depth 1 https://github.com/epsilonrt/mbpoll.git
cmake -S /tmp/mbpoll -B /tmp/mbpoll/build
cmake --build /tmp/mbpoll/build --parallel 2
sudo make -C /tmp/mbpoll/build install
sudo ldconfig
command -v mbpoll
mbpoll -V
```

If CMake reports that the archived `libmodbus-dev` version is too old, build a newer libmodbus first, then repeat the `mbpoll` commands above:

```bash
cd /tmp
git clone --depth 1 https://github.com/stephane/libmodbus.git
cd /tmp/libmodbus
./autogen.sh
./configure
make -j2
sudo make install
sudo ldconfig
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH:-}
```

Do not continue until `command -v mbpoll` returns `/usr/local/bin/mbpoll` (or another executable path) and `mbpoll -V` succeeds. The [upstream mbpoll build instructions](https://github.com/epsilonrt/mbpoll#build-from-source) cover this dependency in more depth.

## 5. Build and copy the dashboard updater

On the development PC, from the repository root, create the self-contained updater. This is the supported first-install path; it creates `/opt/solar_assistant`, the restricted `solar-dashboard` account, the persistent state directory, and the systemd service.

```powershell
py -3 deploy/build_update_bundle.py
py -3 deploy/solar-dashboard-update.pyz --check
scp deploy/solar-dashboard-update.pyz "ORANGE_PI_USER@ORANGE_PI_IP:~/"
```

Back on the Orange Pi, confirm the copied file has not been damaged and install it:

```bash
python3 ~/solar-dashboard-update.pyz --check
sudo python3 ~/solar-dashboard-update.pyz
```

The updater normally tries `apt-get install mbpoll` when `mbpoll` is absent. Because you completed step 4 first, it detects the installed executable and does not attempt that unavailable Buster package.

## 6. Connect and validate the USB Modbus adapter

Shut the inverter down or follow its vendor-approved connection procedure before attaching the USB-to-RS-232 adapter. Do not use an RS-485 adapter or connect RS-232 signals to an RS-485 A/B terminal. Connect the adapter, then identify its stable device name:

```bash
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
dmesg | tail -n 30
```

The service defaults to `/dev/ttyUSB0`, 9600 baud, and slave ID 1. Test those values as the service user:

```bash
id solar-dashboard
sudo -u solar-dashboard test -r /dev/ttyUSB0 && echo "read access OK"
sudo -u solar-dashboard test -w /dev/ttyUSB0 && echo "write access OK"
sudo -u solar-dashboard mbpoll -m rtu -b 9600 -P none -t 4 -a 1 -r 89 -c 1 -1 -q /dev/ttyUSB0
```

The last command reads one register; it does not write inverter settings. If it reports a timeout, stop and verify the RS-232 cable or null-modem requirement, TX/RX/GND wiring, baud rate, slave ID, parity, and that the inverter's RS-232 port uses Modbus RTU before changing application code.

If the adapter appears as `/dev/ttyUSB1` or changes after a reboot, create a stable udev symlink and then set `INVERTER_SERIAL_DEVICE` in the service override. Do not rely on a changing USB number.

## 7. Start and verify the dashboard

```bash
sudo systemctl enable --now solar-inverter-dashboard.service
systemctl is-active solar-inverter-dashboard.service
curl -fsS http://127.0.0.1:8080/api/state
sudo journalctl -u solar-inverter-dashboard.service -n 100 --no-pager
```

`is-active` must print `active`; the API must return JSON. Open `http://ORANGE_PI_IP:8080` only from the trusted LAN to confirm the dashboard renders. If readings are unavailable, the journal output distinguishes a missing `mbpoll` binary, serial permission error, and Modbus communication error.

## 8. Optional: private remote access with Tailscale

Keep the Python service on loopback and publish it only through Tailscale Serve:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
sudo tailscale set --hostname=solar-inverter
sudo tailscale serve --bg http://127.0.0.1:8080
sudo tailscale serve status
```

Complete the authorization URL printed by `tailscale up`, then open the HTTPS address shown by `tailscale serve status`. Do not use Funnel unless public, unauthenticated access is explicitly intended.

## Recovery and next updates

- To inspect service failures: `sudo journalctl -u solar-inverter-dashboard.service -f`
- To check the USB adapter after reconnecting it: `ls -l /dev/ttyUSB*` and `dmesg | tail -n 30`
- To apply a later dashboard release: build and copy a new `solar-dashboard-update.pyz`, then run `sudo python3 ~/solar-dashboard-update.pyz`.
- Do not run `git clean` under `/opt/solar_assistant`; it can remove register logs.

For the ongoing operational procedure, troubleshooting, and Tailscale details, continue with [ORANGE_PI_DEPLOYMENT.md](ORANGE_PI_DEPLOYMENT.md).

## References

- [Orange Pi 3 LTS official resources](https://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/service-and-support/Orange-pi-3-LTS.html)
- [Debian archive guidance](https://www.debian.org/distrib/archive.en.html)
- [Debian Buster release and end-of-support information](https://www.debian.org/releases/buster/)
- [mbpoll upstream build instructions](https://github.com/epsilonrt/mbpoll#build-from-source)
