# Solar Inverter Android

This Android application displays the complete existing Solar Inverter Web dashboard, including live data, demo mode, charts, register logging and CSV downloads, settings, translations, and the LCD tab. The Python dashboard must remain running on a computer connected to the inverter; the phone connects to that computer over LAN, VPN, or Tailscale.

Version 1.6 uses the refined responsive energy-flow cards, component-matched gauge colors, updated inverter and battery graphics, corrected flow states, and complete Ukrainian, Russian, and English dashboard translations.

## Install

1. Copy `Solar-Inverter.apk` to the Android phone.
2. Allow installation from the file-manager/browser when Android asks.
3. Install and open **Solar Inverter**.
4. Enter the dashboard address, for example `http://192.168.1.50:8080` or a Tailscale address.

Use the gear button to change the address. CSV register logs downloaded from the dashboard are saved to the phone's Downloads folder.

## Build

Set `ANDROID_HOME` or `ANDROID_SDK_ROOT`, then run:

```powershell
./gradlew.bat assembleDebug
```

The APK is created under `app/build/outputs/apk/debug/`. The repository build process also copies the installable debug APK to `android_app/Solar-Inverter.apk`.
