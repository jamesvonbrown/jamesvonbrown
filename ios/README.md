# FlipScan for iOS (native)

A SwiftUI client for the same server the web app talks to. Same deals, same
numbers, native feel — plus real APNs notifications from your own app icon.

## Read this first

**These sources have never been compiled.** They were written on Linux, where
no Swift toolchain or iOS SDK exists, so nothing here has been through a
compiler or a simulator. Treat the first build as a debugging session: expect
to fix a handful of type and API-availability errors, most likely around
`NavigationStack`, strict-concurrency warnings, and `AsyncImage` phases.

If you want something working on the phone *today*, use the web app instead —
it's complete, tested, and installs to the Home Screen from Safari with its own
icon and full-screen chrome. See the main README. This target is here so that
the day you have a Mac, the work is already done.

## Requirements

- macOS with Xcode 15 or newer (iOS 17 deployment target)
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) — `brew install xcodegen`
- An Apple Developer Program membership ($99/yr), but **only** for push
  notifications and installing to a physical device. The simulator needs
  neither.

## Build

```bash
cd ios
xcodegen generate
open FlipScan.xcodeproj
```

Then in Xcode: select a simulator, hit Run. On first launch the app asks for
your server URL and the `FLIPSCAN_API_TOKEN` from the server's `.env`.

To run on a real phone, set `DEVELOPMENT_TEAM` in `project.yml` to your team id
and re-run `xcodegen generate`.

`FlipScan.xcodeproj` is intentionally **not** committed — it's generated from
`project.yml`, which avoids the merge conflicts that Xcode project files are
famous for.

## Push notifications

The app works fine without them; alerts arrive through ntfy on the phone
instead. To use native APNs:

1. In the Apple Developer portal, create an **APNs Auth Key** (`.p8`). Note the
   Key ID and your Team ID.
2. Copy the `.p8` onto the server and set:
   ```
   FLIPSCAN_NOTIFY__APNS_KEY_ID=ABC123DEFG
   FLIPSCAN_NOTIFY__APNS_TEAM_ID=YOURTEAMID
   FLIPSCAN_NOTIFY__APNS_KEY_PATH=/path/to/AuthKey_ABC123DEFG.p8
   FLIPSCAN_NOTIFY__APNS_BUNDLE_ID=com.flipscan.app
   FLIPSCAN_NOTIFY__APNS_USE_SANDBOX=true
   FLIPSCAN_NOTIFY__CHANNELS=ntfy,apns
   ```
   Set `APNS_USE_SANDBOX=false` for TestFlight or App Store builds — a
   development token sent to the production endpoint fails silently, which is
   an annoying afternoon to debug.
3. In the app, go to Settings → Enable push notifications. The device token
   registers itself with the server automatically.

## Layout

| File | What it does |
|---|---|
| `project.yml` | XcodeGen spec — the project file's source of truth |
| `FlipScan/FlipScanApp.swift` | Entry point, app delegate, APNs registration |
| `FlipScan/Models.swift` | Codable mirrors of the server's response schemas |
| `FlipScan/APIClient.swift` | Networking actor, auth, tolerant date decoding |
| `FlipScan/AppState.swift` | Observable state + Keychain token storage |
| `FlipScan/Views/` | Setup, deal list, deal detail, runs, settings |

The token is kept in the Keychain rather than `UserDefaults`, which is
plain-text inside the app container.

## Known rough edges

- **Never compiled** (see above).
- Thresholds are read-only here. The profit bar and drive radius live on the
  server because they govern scanning, not just display — edit them in the web
  app at `/app/#/settings`.
- No offline cache. The list needs the server reachable.
- No map view yet. `PickupRun` carries `centerLat`/`centerLon`, so a MapKit
  view of the day's route is a small addition when you want it.
