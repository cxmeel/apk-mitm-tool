# APK MITM GUI Utility

A cross-platform graphical user interface (GUI) wrapper for the powerful [apk-mitm](https://github.com/niklashigi/apk-mitm) tool. This utility allows you to easily bypass Android certificate pinning by patching APKs directly from your PC or by pulling them straight from your connected Android device.

## Features
- **Fetch from Device**: Pull user-installed apps directly from your connected Android device via USB or Wireless Debugging.
- **App Bundle Support**: Automatically handles modern Split APKs (App Bundles). Extracts, bundles, patches, and re-installs the complete set of splits seamlessly.
- **Drag & Drop**: Simply drag and drop an `.apk` file onto the window to begin patching.
- **Auto ADB Management**: Automatically downloads and configures ADB (Android Debug Bridge) if it's not already installed on your system.
- **One-Click Install**: Installs the newly patched APK right back to your device with a single click.

## Prerequisites
- **Python 3.8+**
- **Node.js** (Required for the underlying `apk-mitm` tool. A Node package manager like `npx`, `pnpx`, `yarn`, or `bunx` must be in your PATH).

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/apk-mitm-tool.git
   cd apk-mitm-tool
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

4. **Usage:**
   - Click "Fetch from Device" to automatically pull an installed app, or drag and drop a local `.apk` into the window.
   - Click "Patch APK".
   - Once complete, click "Install Patched APK" to push it directly back to your device.

## Release Versioning

- The canonical app/release version lives in `VERSION` and is currently `v0.1.0`.
- GitHub Actions now checks that manifest on pushes to `main` and only builds/releases when the version changes from the latest published tag.
- To publish a new release, bump the version in `VERSION` using the `vX.Y.Z` format and push the change to `main`.
- Release tags are created automatically from that manifest version, and Windows binaries receive matching file/product version metadata.

## Binary Signing

- GitHub Actions does not automatically Authenticode-sign Windows executables.
- GitHub artifact attestations/provenance can help prove how a binary was built, but they do not replace Windows code signing or SmartScreen reputation.
- To reduce Windows Defender/SmartScreen warnings, add a real code-signing step in CI using your signing certificate or a managed signing service.

## Attribution
This GUI is a wrapper built around the amazing [apk-mitm](https://github.com/niklashigi/apk-mitm) command-line tool created by [niklashigi](https://github.com/niklashigi). All core certificate patching logic is handled by their tool!

---

Created with [✨ Gemini 3.1 Pro](https://antigravity.google/)
