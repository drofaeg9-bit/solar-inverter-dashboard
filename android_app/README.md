# Solar Invertor Android

This Android application displays the existing Solar Invertor Web dashboard. The Python dashboard must remain running on a computer connected to the inverter; the phone connects to that computer over LAN, VPN, or Tailscale.

## Install

1. Copy `SolarInvertor-debug.apk` to the Android phone.
2. Allow installation from the file-manager/browser when Android asks.
3. Install and open **Solar Invertor**.
4. Enter the dashboard address, for example `http://192.168.1.50:8080` or a Tailscale address.

Use the gear button to change the address. CSV register logs downloaded from the dashboard are saved to the phone's Downloads folder.

## Build

Set `ANDROID_HOME` or `ANDROID_SDK_ROOT`, then run:

```powershell
./gradlew.bat assembleDebug
```

The APK is created under `app/build/outputs/apk/debug/`.
