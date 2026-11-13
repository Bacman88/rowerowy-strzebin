#!/usr/bin/env bash
# Dopisuje uprawnienia do AndroidManifest.xml wygenerowanego przez `npx cap add android`.
set -euo pipefail
M="$(dirname "$0")/android/app/src/main/AndroidManifest.xml"
for p in ACCESS_COARSE_LOCATION ACCESS_FINE_LOCATION FOREGROUND_SERVICE FOREGROUND_SERVICE_LOCATION POST_NOTIFICATIONS VIBRATE WAKE_LOCK; do
  grep -q "android.permission.$p\"" "$M" || sed -i "s|</manifest>|    <uses-permission android:name=\"android.permission.$p\" />\n</manifest>|" "$M"
done
# synteza mowy (Android 11+: widoczność usług TTS)
grep -q "TTS_SERVICE" "$M" || sed -i 's|</manifest>|    <queries><intent><action android:name="android.intent.action.TTS_SERVICE" /></intent></queries>\n</manifest>|' "$M"
grep -c "uses-permission" "$M"
# nazwa kanału powiadomienia nawigacji (Ustawienia → Powiadomienia)
S="$(dirname "$0")/android/app/src/main/res/values/strings.xml"
grep -q capacitor_background_geolocation_notification_channel_name "$S" || sed -i 's|</resources>|    <string name="capacitor_background_geolocation_notification_channel_name">Nawigacja</string>\n</resources>|' "$S"
