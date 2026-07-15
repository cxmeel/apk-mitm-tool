import os
import sys
import shutil
import zipfile
import subprocess
import urllib.request
import platform

def get_app_data_dir():
    if platform.system() == 'Windows':
        base = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        return os.path.join(base, 'apk-mitm-tool')
    else:
        return os.path.join(os.path.expanduser('~'), '.apk-mitm-tool')

APP_DATA_DIR = get_app_data_dir()
ADB_DIR = os.path.join(APP_DATA_DIR, 'platform-tools')

def get_adb_path():
    # 1. Check if ADB is in the persistent directory
    local_adb = os.path.join(ADB_DIR, 'adb.exe' if platform.system() == 'Windows' else 'adb')
    if os.path.exists(local_adb):
        return local_adb
    
    # 2. Check if ADB is in PATH (validate before returning)
    system_adb = shutil.which('adb')
    if system_adb and is_adb_valid(system_adb):
        return system_adb
    
    return None

def is_adb_valid(adb_path):
    try:
        kwargs = {}
        if platform.system() == 'Windows':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        res = subprocess.run([adb_path, "version"], capture_output=True, **kwargs)
        return res.returncode == 0
    except Exception:
        return False

def ensure_adb(log_callback=None):
    local_adb = os.path.join(ADB_DIR, 'adb.exe' if platform.system() == 'Windows' else 'adb')
    system_adb = shutil.which('adb')
    
    # If the user has a system-wide ADB, we'll just use that and skip our own updates.
    if system_adb and is_adb_valid(system_adb):
        return system_adb

    system = platform.system().lower()
    if system == 'windows':
        url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
    elif system == 'darwin':
        url = "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
    elif system == 'linux':
        url = "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
    else:
        raise Exception(f"Unsupported OS for automatic ADB download: {system}")
        
    etag_file = os.path.join(APP_DATA_DIR, 'adb_etag.txt')
    current_etag = ""
    if os.path.exists(etag_file):
        with open(etag_file, 'r') as f:
            current_etag = f.read().strip()

    is_valid = os.path.exists(local_adb) and is_adb_valid(local_adb)
    
    remote_etag = None
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as res:
            remote_etag = res.headers.get('ETag', '').strip('"')
    except Exception:
        pass # Ignore network errors during update check
        
    if is_valid and (not remote_etag or remote_etag == current_etag):
        return local_adb
        
    if log_callback:
        if not is_valid:
            log_callback("ADB missing or corrupted. Downloading...\n")
        else:
            log_callback("A new version of ADB is available. Updating...\n")
            
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    zip_path = os.path.join(APP_DATA_DIR, "platform-tools.zip")
    
    try:
        import requests
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except ImportError:
        urllib.request.urlretrieve(url, zip_path)
        
    if log_callback:
        log_callback("Extracting ADB...\n")
        
    shutil.rmtree(ADB_DIR, ignore_errors=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(APP_DATA_DIR)
        
    os.remove(zip_path)
    
    if remote_etag:
        with open(etag_file, 'w') as f:
            f.write(remote_etag)
            
    if system != 'windows' and os.path.exists(local_adb):
        os.chmod(local_adb, 0o755)

    if not os.path.exists(local_adb) or not is_adb_valid(local_adb):
        raise Exception(f"ADB extraction failed or binary not found at: {local_adb}")

    return local_adb

def run_adb_command(args, log_callback=None, check=True):
    adb = get_adb_path()
    if not adb:
        adb = ensure_adb(log_callback)
        
    cmd = [adb] + args
    if log_callback:
        log_callback(f"> {' '.join(cmd)}")
        
    # On Windows, we can use creationflags to prevent cmd window from popping up
    kwargs = {}
    if platform.system() == 'Windows':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if check and result.returncode != 0:
        if log_callback:
            log_callback(f"Command failed: {result.stderr}")
        raise Exception(f"ADB command failed: {result.stderr}")
        
    return result.stdout.strip()

def get_devices():
    output = run_adb_command(['devices', '-l'])
    devices = []
    lines = output.splitlines()
    for line in lines[1:]: # Skip 'List of devices attached'
        if line.strip():
            parts = line.split()
            if len(parts) >= 2:
                dev_id = parts[0]
                status = parts[1]
                model = "Unknown Device"
                for p in parts[2:]:
                    if p.startswith('model:'):
                        model = p.split(':', 1)[1].replace('_', ' ')
                devices.append({'id': dev_id, 'status': status, 'model': model})
    return devices

def pair_device(ip_port, code, log_callback=None):
    # pair IP:PORT pairing_code
    return run_adb_command(['pair', ip_port, code], log_callback=log_callback, check=False)

def connect_device(ip_port, log_callback=None):
    return run_adb_command(['connect', ip_port], log_callback=log_callback, check=False)

def list_packages(device_id=None, show_system=False):
    args = ['shell', 'pm', 'list', 'packages', '-f']
    if not show_system:
        args.insert(4, '-3')
    if device_id:
        args = ['-s', device_id] + args
        
    output = run_adb_command(args)
    packages = []
    for line in output.splitlines():
        if line.startswith('package:'):
            # Format: package:/data/app/.../base.apk=com.example.app
            line = line[8:]
            if '=' in line:
                path, pkg = line.rsplit('=', 1)
                packages.append({'package': pkg, 'path': path})
                
    # Sort alphabetically by package name
    packages.sort(key=lambda x: x['package'].lower())
    return packages

def pull_apk(device_id, pkg_name, dest_dir, log_callback=None):
    args = ['shell', 'pm', 'path', pkg_name]
    if device_id:
        args = ['-s', device_id] + args
    output = run_adb_command(args, log_callback=log_callback)
    
    paths = []
    for line in output.splitlines():
        if line.startswith('package:'):
            paths.append(line[8:].strip())
            
    if not paths:
        raise Exception(f"Could not find paths for package {pkg_name}")
        
    if len(paths) == 1:
        local_dest = os.path.join(dest_dir, f"{pkg_name}.apk")
        args_pull = ['pull', paths[0], local_dest]
        if device_id:
            args_pull = ['-s', device_id] + args_pull
        run_adb_command(args_pull, log_callback=log_callback)
        return local_dest
    else:
        if log_callback:
            log_callback(f"Found {len(paths)} split APKs. Bundling into .apks...\n")
            
        temp_pull_dir = os.path.join(dest_dir, pkg_name)
        os.makedirs(temp_pull_dir, exist_ok=True)
        
        for p in paths:
            args_pull = ['pull', p, temp_pull_dir]
            if device_id:
                args_pull = ['-s', device_id] + args_pull
            run_adb_command(args_pull, log_callback=log_callback)
            
        apks_path = os.path.join(dest_dir, f"{pkg_name}.apks")
        with zipfile.ZipFile(apks_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_pull_dir):
                for f in files:
                    file_path = os.path.join(root, f)
                    arcname = os.path.relpath(file_path, temp_pull_dir)
                    zipf.write(file_path, arcname)
                    
        shutil.rmtree(temp_pull_dir, ignore_errors=True)
        return apks_path

def install_apk(device_id, local_apk_path, log_callback=None):
    if local_apk_path.endswith('.apks') or local_apk_path.endswith('.xapk'):
        if log_callback:
            log_callback(f"Extracting bundle {os.path.basename(local_apk_path)} for installation...\n")
        temp_dir = local_apk_path + "_extracted"
        os.makedirs(temp_dir, exist_ok=True)
        with zipfile.ZipFile(local_apk_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        apk_files = []
        for root, _, files in os.walk(temp_dir):
            for f in files:
                if f.endswith('.apk'):
                    apk_files.append(os.path.join(root, f))
                    
        if not apk_files:
            raise Exception("No APK files found inside the bundle.")
            
        args = ['install-multiple', '-r'] + apk_files
        if device_id:
            args = ['-s', device_id] + args
            
        try:
            result = run_adb_command(args, log_callback=log_callback)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return result
    else:
        args = ['install', '-r', local_apk_path]
        if device_id:
            args = ['-s', device_id] + args
        return run_adb_command(args, log_callback=log_callback)
