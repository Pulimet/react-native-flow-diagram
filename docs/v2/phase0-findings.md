# Phase 0 findings: pulling run files from release builds

Date: 2026-11-24. Host: macOS, Xcode 27.0 (27A266a), Android emulator Pixel_9.

## Results

| Target | Build | Result |
|---|---|---|
| Android emulator (API 35), primary `getExternalFilesDir` + `adb pull` | release | PASS |
| Android emulator (API 35), fallback `MediaStore.Downloads` + `adb pull` | release | PASS |
| iOS simulator (iPhone 16 Pro), Documents via `simctl get_app_container` | Release | PASS |
| Android physical device | release | Pending |
| iOS physical device | Release + Development signing | Pending |

## What was built

- `RunFileWriter.kt` (Android) and `RunFileWriter.swift` (iOS) in the library. When the launch carries the flag and a run id, they write `run_start`, two `event` lines and `run_end` as JSON Lines. Called from `MainActivity.onCreate` and `AppDelegate.didFinishLaunchingWithOptions`.
- Android extra `FlowDiagramSink=downloads` selects the MediaStore fallback (spike only).
- Host script: `py/spike/phase0_fetch.py` (stdlib only). Removed in Phase 4, replaced by `py/src/flow/platforms/`; see git history before that commit. The commands below that call it are historical.

## Commands run

Android (from `android/`):

```
./gradlew assembleRelease          # about 16 min cold, release signed with debug keystore
adb install -r app/build/outputs/apk/release/app-release.apk
adb shell dumpsys package com.flowdiagram | grep -i flags
python3 modules/react-native-flow-diagram/py/spike/phase0_fetch.py --target android
python3 modules/react-native-flow-diagram/py/spike/phase0_fetch.py --target android_downloads
```

- Emulator API level: 35.
- Debuggable: `pkgFlags=[ HAS_CODE ALLOW_CLEAR_USER_DATA ]`, no `DEBUGGABLE`. The file also records `"debuggable":false`. Confirmed release.
- Primary path: `/sdcard/Android/data/com.flowdiagram/files/flowdiagram/runs/<runId>.jsonl`, pulled fine by `adb pull` on API 35 (shell has access).
- Fallback path: `/sdcard/Download/flowdiagram/com.flowdiagram/<runId>.jsonl`, written via MediaStore, no permissions needed, pulled fine.
- R8/minify is off in the template (`minifyEnabled false`), so R8 was not exercised. Revisit with minify on.

iOS simulator:

```
cd ios && pod install
xcodebuild -workspace ios/FlowDiagram.xcworkspace -scheme FlowDiagram -configuration Release \
  -sdk iphonesimulator -destination 'id=<sim-udid>' -derivedDataPath <dd> build
xcrun simctl boot <sim-udid>
xcrun simctl install booted <dd>/Build/Products/Release-iphonesimulator/FlowDiagram.app
python3 modules/react-native-flow-diagram/py/spike/phase0_fetch.py --target ios_simulator
```

The script runs `simctl launch --terminate-running-process booted <bundle> --flowDiagramFlag --flowDiagramRunId <id>`, then reads `<data container>/Documents/flowdiagram/runs/<id>.jsonl`.

## Issues

- Xcode 27 fails to compile the `fmt` pod (`consteval ... is not a constant expression`) under C++20. Fixed in `ios/Podfile` post_install by building the `fmt` target as C++17.
- `pod install` updates `ios/Podfile.lock` after the Podfile change; committed to keep pods in sync.
- ATS and permissions: no issue. App Documents needs no entitlement. The sample's HTTPS request is unaffected.
- Release build bundles JS (`main.jsbundle`), no Metro needed.

## Physical device results

| Target | Device | Build | Result |
|---|---|---|---|
| Android primary path | Samsung SM-S928B, Android 17 (API 37) | Release APK, not debuggable | PASS |
| Android Downloads fallback | Samsung SM-S928B, Android 17 (API 37) | Release APK, not debuggable | PASS |
| iOS device | iPhone 16 Pro Max | Release, Apple Development (personal team) | PASS |

iOS device notes:

- The device must be registered in the team's profile (`-allowProvisioningDeviceRegistration`).
- With a personal team the launch is denied ("profile has not been explicitly trusted") until Settings > General > VPN & Device Management > developer certificate > Trust. Uninstalling the app removes that trust; trust again after reinstalling.
- Developer Mode must be on and the phone unlocked for build, install and launch.

## How to run the physical device checks

Android device (USB debugging on, release APK installed):

```
adb -s <serial> install -r android/app/build/outputs/apk/release/app-release.apk
python3 modules/react-native-flow-diagram/py/spike/phase0_fetch.py --target android --serial <serial>
python3 modules/react-native-flow-diagram/py/spike/phase0_fetch.py --target android_downloads --serial <serial>
```

On Android 11+ some OEMs may restrict `adb pull` from `Android/data` on-device; the shell user normally can read it. If primary fails, the Downloads fallback is the test.

iOS device (trusted, Developer Mode on, replace `<team-id>`, `<udid>`):

```
xcodebuild -workspace ios/FlowDiagram.xcworkspace -scheme FlowDiagram -configuration Release \
  -destination 'id=<udid>' -derivedDataPath build-dev DEVELOPMENT_TEAM=<team-id> \
  CODE_SIGN_STYLE=Automatic -allowProvisioningUpdates build
xcrun devicectl device install app --device <udid> build-dev/Build/Products/Release-iphoneos/FlowDiagram.app
python3 modules/react-native-flow-diagram/py/spike/phase0_fetch.py --target ios_device --udid <udid>
```

The script runs `xcrun devicectl device process launch --terminate-existing --device <udid> <bundle> -- --flowDiagramFlag --flowDiagramRunId <id>` then `xcrun devicectl device copy from --device <udid> --domain-type appDataContainer --domain-identifier <bundle> --source Documents/flowdiagram/runs/<id>.jsonl --destination <local>`. If the bundle id differs after signing, pass `--bundle`.
