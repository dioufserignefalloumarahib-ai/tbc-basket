# THIADIAYE BASKET CLUB WebView Mobile

This folder contains starter projects for a mobile WebView app that loads your Flask app.

## Android

Open the folder `android_app` in Android Studio.

Important: update the URL in `MainActivity.kt` to your real deployed URL or local IP.

Example:

```kotlin
webView.loadUrl("https://mon-site.com")
```

## iPhone

Open the folder `ios_app` in Xcode.

Update the URL in `ViewController.swift` to your deployed URL.

## Recommended setup

For production use, host your Flask app online and set the app to load HTTPS.

For local testing, use a local network IP such as:

```text
http://192.168.1.25:5000
```
