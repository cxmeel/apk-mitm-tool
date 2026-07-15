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
  - *Note: If you installed Node.js using a version manager like `fnm` or `nvm`, Node may only be available in your terminal profile. If you launch the pre-compiled `.exe` by double-clicking it from Windows Explorer, it will not have access to your terminal's `PATH` and will fail to find Node. To fix this, either launch the `.exe` directly from your PowerShell terminal, or open the app's **Advanced Settings** and set a Custom Executor Path pointing to your `npx.cmd` file.*

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

## Attribution
This GUI is a wrapper built around the amazing [apk-mitm](https://github.com/niklashigi/apk-mitm) command-line tool created by [niklashigi](https://github.com/niklashigi). All core certificate patching logic is handled by their tool!

---

Created with [✨ Gemini 3.1 Pro](https://antigravity.google/)
