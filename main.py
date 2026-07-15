import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
from tkinterdnd2 import TkinterDnD, DND_FILES
import os
import sys
import threading
import tempfile
import shutil
import platform

import adb_manager
import patcher
import config
import versioning

class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        
        # Check Node.js and select executor
        self.executor_cmd = self.check_node_and_executor()
        if not self.executor_cmd:
            sys.exit(1)

        try:
            self.app_version = versioning.read_version()
        except (OSError, ValueError):
            self.app_version = "unknown"

        self.title(f"APK MITM Utility {self.app_version}")
        self.geometry("600x500")

        self.selected_apk_path = tk.StringVar()
        self.patched_apk_path = None
        self.temp_dir = tempfile.mkdtemp(prefix="apk_mitm_")
        self.is_patching = False
        self.app_config = config.load_config()
        self.current_patch_task = None
        
        # Menu bar
        menu_bar = tk.Menu(self)
        settings_menu = tk.Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="Advanced Settings...", command=self.open_settings)
        menu_bar.add_cascade(label="Settings", menu=settings_menu)
        self.config(menu=menu_bar)

        self.create_widgets()
        
        # Setup drag and drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop)
        
        self.log(
            f"APK MITM Utility {self.app_version}\n"
            f"Node.js verified. Using '{' '.join(self.executor_cmd)}' for apk-mitm.\n"
        )
        
    def open_settings(self):
        SettingsDialog(self)
        
    def check_node_and_executor(self):
        import subprocess
        
        def is_installed(cmd):
            if shutil.which(cmd):
                return True
            try:
                # Fallback to shell resolution for PyInstaller exes where PATH might be wonky
                flags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                res = subprocess.run([cmd, "--version"], capture_output=True, shell=True, creationflags=flags)
                return res.returncode == 0
            except Exception:
                return False

        if not is_installed("node"):
            messagebox.showerror("Node.js Required", "Node.js is not installed or not in PATH.\n\nPlease install Node.js from https://nodejs.org/ and relaunch the application.")
            return None
            
        if is_installed("npx"):
            return ["npx", "-y"]
        elif is_installed("pnpx"):
            return ["pnpx", "-y"]
        elif is_installed("yarn"):
            return ["yarn", "dlx"]
        elif is_installed("bunx"):
            return ["bunx", "-y"]
            
        messagebox.showerror("Executor Required", "Could not find npx, pnpx, yarn, or bunx in PATH.\n\nPlease install a Node package manager.")
        return None

    def create_widgets(self):
        # File selection frame
        file_frame = tk.Frame(self)
        file_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(file_frame, text="APK File:").pack(side=tk.LEFT)
        self.entry_apk = tk.Entry(file_frame, textvariable=self.selected_apk_path, state='readonly')
        self.entry_apk.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.btn_browse = tk.Button(file_frame, text="Browse", command=self.browse_apk)
        self.btn_browse.pack(side=tk.LEFT, padx=2)

        # Device selection frame
        dev_frame = tk.Frame(self)
        dev_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(dev_frame, text="Device:").pack(side=tk.LEFT)
        self.device_combo = ttk.Combobox(dev_frame, state="readonly", width=30)
        self.device_combo.pack(side=tk.LEFT, padx=5)
        
        self.btn_refresh = tk.Button(dev_frame, text="Refresh", command=self.refresh_devices)
        self.btn_refresh.pack(side=tk.LEFT, padx=2)
        
        self.btn_pair = tk.Button(dev_frame, text="Pair Wireless...", command=self.pair_wireless_device)
        self.btn_pair.pack(side=tk.LEFT, padx=2)
        
        self.btn_fetch = tk.Button(dev_frame, text="📱 Fetch from Device", command=self.fetch_from_device)
        self.btn_fetch.pack(side=tk.LEFT, padx=2)

        # Action buttons
        action_frame = tk.Frame(self)
        action_frame.pack(fill=tk.X, padx=10, pady=5)

        self.btn_patch = tk.Button(action_frame, text="Patch APK", command=self.start_patching)
        self.btn_patch.pack(side=tk.LEFT, padx=2)
        
        self.btn_cancel = tk.Button(action_frame, text="Cancel", command=self.cancel_patching, state=tk.DISABLED, fg="red")
        self.btn_cancel.pack(side=tk.LEFT, padx=2)
        
        self.btn_continue = tk.Button(action_frame, text="Continue", command=self.continue_patching, state=tk.DISABLED, fg="blue")
        self.btn_continue.pack(side=tk.LEFT, padx=2)

        self.btn_install = tk.Button(action_frame, text="Install Patched APK", command=self.install_patched, state=tk.DISABLED)
        self.btn_install.pack(side=tk.LEFT, padx=2)

        self.btn_explorer = tk.Button(action_frame, text="Show in Explorer", command=self.show_in_explorer, state=tk.DISABLED)
        self.btn_explorer.pack(side=tk.LEFT, padx=2)

        # Status bar must be packed BEFORE the expanding log frame so it stays anchored to the bottom
        status_frame = tk.Frame(self)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', length=100)
        self.progress.pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(status_frame, text="Ready", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Logs
        log_frame = tk.Frame(self)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(log_frame, text="Logs:").pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(log_frame, state=tk.DISABLED, bg="#f0f0f0")
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Ensure ADB is available
        self.log("Initializing ADB...\n")
        threading.Thread(target=self.init_adb, daemon=True).start()

    def set_ui_state(self, state):
        self.btn_browse.config(state=state)
        self.btn_fetch.config(state=state)
        self.device_combo.config(state=state)
        self.btn_refresh.config(state=state)
        self.btn_pair.config(state=state)
        
        if state == tk.DISABLED:
            self.btn_patch.config(state=tk.DISABLED)
            self.btn_install.config(state=tk.DISABLED)
            self.btn_explorer.config(state=tk.DISABLED)
            if self.is_patching:
                self.btn_cancel.config(state=tk.NORMAL)
                if self.app_config.get("wait_for_manual_changes"):
                    self.btn_continue.config(state=tk.NORMAL)
        else:
            self.btn_patch.config(state=tk.NORMAL if self.selected_apk_path.get() else tk.DISABLED)
            self.btn_install.config(state=tk.NORMAL if self.patched_apk_path else tk.DISABLED)
            self.btn_explorer.config(state=tk.NORMAL if self.patched_apk_path else tk.DISABLED)
            self.btn_cancel.config(state=tk.DISABLED)
            self.btn_continue.config(state=tk.DISABLED)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.update_idletasks()

    def init_adb(self):
        try:
            adb_path = adb_manager.get_adb_path()
            if not adb_path:
                self.log("ADB not found. Downloading platform-tools...\n")
                adb_path = adb_manager.download_adb(log_callback=lambda msg: self.log(msg + "\n"))
            self.log(f"ADB is ready: {adb_path}\n\n")
            # Schedule initial device refresh on main thread
            self.after(0, self.refresh_devices)
        except Exception as e:
            self.log(f"Error initializing ADB: {e}\n")

    def refresh_devices(self):
        devices = adb_manager.get_devices()
        dev_list = [f"{d['model']} ({d['id']})" for d in devices]
        self.device_combo['values'] = dev_list
        if dev_list:
            self.device_combo.current(0)
        else:
            self.device_combo.set("No devices found")

    def on_drop(self, event):
        if self.is_patching:
            return
            
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
            
        valid_extensions = ('.apk', '.apks', '.xapk')
        if not file_path.lower().endswith(valid_extensions):
            messagebox.showerror("Invalid File", "Please drop a valid .apk, .apks, or .xapk file.")
            return
            
        self.selected_apk_path.set(file_path)
        self.btn_install.config(state=tk.DISABLED)
        self.btn_explorer.config(state=tk.DISABLED)
        self.patched_apk_path = None

    def browse_apk(self):
        filename = filedialog.askopenfilename(
            title="Select App Package",
            filetypes=(("Android Packages", "*.apk *.apks *.xapk"), ("All files", "*.*"))
        )
        if filename:
            self.selected_apk_path.set(filename)
            self.btn_install.config(state=tk.DISABLED)
            self.btn_explorer.config(state=tk.DISABLED)
            self.patched_apk_path = None

    def fetch_from_device(self):
        try:
            selection = self.device_combo.get()
            if not selection or selection == "No devices found":
                messagebox.showwarning("Warning", "No device selected. Please connect a device or pair wirelessly.")
                return
                
            device_id = selection[selection.rfind("(")+1 : selection.rfind(")")]

            self.log(f"Fetching packages from device {device_id}...\n")
            
            def on_selected(pkg_name):
                if pkg_name:
                    selected_pkg = next((p for p in packages if p['package'] == pkg_name), None)
                    if selected_pkg:
                        self.pull_apk_from_device(device_id, selected_pkg)
                        
            def reload_packages(show_sys):
                self.app_config["show_system_apps"] = show_sys
                config.save_config(self.app_config)
                nonlocal packages
                packages = adb_manager.list_packages(device_id, show_system=show_sys)
                return [p['package'] for p in packages]

            packages = adb_manager.list_packages(device_id, show_system=self.app_config.get("show_system_apps", False))
            pkg_names = [p['package'] for p in packages]
            
            if not packages:
                messagebox.showinfo("Packages", "No packages found on device.")
                # We still allow opening dialog to toggle system apps if they want
            
            ListDialog(self, "Select Application", "Choose an app to fetch:", pkg_names, 
                       on_selected=on_selected, reload_callback=reload_packages)
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch from device: {e}")
            self.log(f"Error fetching from device: {e}\n")

    def pair_wireless_device(self):
        pair_window = tk.Toplevel(self)
        pair_window.title("Pair Wireless Device")
        pair_window.geometry("380x250")
        pair_window.transient(self)
        pair_window.grab_set()
        
        tk.Label(pair_window, text="Go to Developer Options > Wireless Debugging\nand select 'Pair device with pairing code'.\n\nEnter the details below:").pack(pady=10)
        
        frame = tk.Frame(pair_window)
        frame.pack(pady=5)
        
        tk.Label(frame, text="IP & Port (e.g. 192.168.1.50:5555):").grid(row=0, column=0, sticky=tk.W, pady=5)
        entry_ip = tk.Entry(frame, width=20)
        entry_ip.grid(row=0, column=1, padx=5)
        
        tk.Label(frame, text="6-Digit Pairing Code:").grid(row=1, column=0, sticky=tk.W, pady=5)
        entry_code = tk.Entry(frame, width=20)
        entry_code.grid(row=1, column=1, padx=5)
        
        def attempt_pair():
            ip_port = entry_ip.get().strip()
            code = entry_code.get().strip()
            
            if not ip_port or not code:
                messagebox.showerror("Error", "Please enter both IP:Port and Pairing Code.", parent=pair_window)
                return
                
            try:
                self.log(f"Pairing with {ip_port}...\n")
                adb_manager.pair_device(ip_port, code, log_callback=lambda msg: self.log(msg + "\n"))
                self.log(f"Connecting to {ip_port}...\n")
                adb_manager.connect_device(ip_port, log_callback=lambda msg: self.log(msg + "\n"))
                
                messagebox.showinfo("Success", "Device paired and connected successfully. You can now fetch apps.", parent=pair_window)
                self.after(0, self.refresh_devices)
                pair_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to pair device: {e}", parent=pair_window)
                self.log(f"Pairing error: {e}\n")
                
        tk.Button(pair_window, text="Pair & Connect", command=attempt_pair).pack(pady=15)
        
        self.wait_window(pair_window)

    def pull_apk_from_device(self, device_id, pkg_info):
        pkg_name = pkg_info['package']
        
        # Clean temp directory to prevent bloat
        for item in os.listdir(self.temp_dir):
            item_path = os.path.join(self.temp_dir, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
        
        self.log(f"Pulling {pkg_name} from device...\n")
        self.update_idletasks()
        self.set_ui_state(tk.DISABLED)
        self.status_label.config(text="Pulling APK from device...")
        self.progress.start(10)
        
        def pull_thread():
            try:
                local_dest = adb_manager.pull_apk(device_id, pkg_name, self.temp_dir, log_callback=self.safe_log)
                
                self.after(0, lambda: self.selected_apk_path.set(local_dest))
                self.patched_apk_path = None
                self.safe_log(f"Successfully pulled to {local_dest}\n\n")
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to pull APK: {e}"))
                self.safe_log(f"Pull error: {e}\n")
            finally:
                self.after(0, self.progress.stop)
                self.after(0, lambda: self.status_label.config(text="Ready"))
                self.after(0, lambda: self.set_ui_state(tk.NORMAL))
                
        threading.Thread(target=pull_thread, daemon=True).start()

    def start_patching(self):
        apk_path = self.selected_apk_path.get()
        if not apk_path or not os.path.exists(apk_path):
            messagebox.showwarning("Warning", "Please select a valid APK file first.")
            return

        self.btn_patch.config(state=tk.DISABLED)
        self.btn_install.config(state=tk.DISABLED)
        self.btn_explorer.config(state=tk.DISABLED)
        self.patched_apk_path = None
        self.log_text.delete(1.0, tk.END)
        self.log("Starting apk-mitm patch process...\n")
        
        self.is_patching = True
        self.set_ui_state(tk.DISABLED)
        self.status_label.config(text="Patching APK...")
        self.progress.start(10)
        
        self.current_patch_task = patcher.PatchTask(
            apk_path, 
            self.executor_cmd,
            self.app_config,
            log_callback=self.safe_log, 
            done_callback=self.patching_done
        )
        self.current_patch_task.start()

    def cancel_patching(self):
        if self.current_patch_task:
            self.current_patch_task.cancel()
            
    def continue_patching(self):
        if self.current_patch_task:
            self.current_patch_task.resume()

    def safe_log(self, message):
        # Schedule log update on main thread
        self.after(0, lambda: self.log(message))

    def patching_done(self, success, output_path):
        def on_done():
            self.is_patching = False
            self.progress.stop()
            self.status_label.config(text="Ready")
            self.set_ui_state(tk.NORMAL)
            
            if success and output_path and os.path.exists(output_path):
                self.patched_apk_path = output_path
                self.btn_install.config(state=tk.NORMAL)
                self.btn_explorer.config(state=tk.NORMAL)
                messagebox.showinfo("Success", "APK patched successfully!")
            else:
                messagebox.showerror("Error", "Patching failed. Please check the logs.")
        self.after(0, on_done)

    def install_patched(self):
        if not self.patched_apk_path:
            return
            
        selection = self.device_combo.get()
        if not selection or selection == "No devices found":
            messagebox.showwarning("Warning", "No device selected for installation. Please select a device.")
            return
            
        device_id = selection[selection.rfind("(")+1 : selection.rfind(")")]
        self.log(f"\nInstalling {os.path.basename(self.patched_apk_path)} to device {device_id}...\n")
        self.update_idletasks()
        self.set_ui_state(tk.DISABLED)
        self.status_label.config(text="Installing APK...")
        self.progress.start(10)
        
        def install_thread():
            try:
                out = adb_manager.install_apk(device_id, self.patched_apk_path, log_callback=self.safe_log)
                self.safe_log(f"Install output: {out}\n")
                self.after(0, lambda: messagebox.showinfo("Success", "App installed successfully."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to install APK: {e}"))
                self.safe_log(f"Install error: {e}\n")
            finally:
                self.after(0, self.progress.stop)
                self.after(0, lambda: self.status_label.config(text="Ready"))
                self.after(0, lambda: self.set_ui_state(tk.NORMAL))
                
        threading.Thread(target=install_thread, daemon=True).start()

    def show_in_explorer(self):
        if not self.patched_apk_path:
            return
            
        path = os.path.dirname(self.patched_apk_path)
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def on_closing(self):
        if self.is_patching:
            if not messagebox.askyesno("Exit", "Process is currently running. Are you sure you want to exit?"):
                return
                
        # Cleanup temp dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.destroy()

class ListDialog(tk.Toplevel):
    def __init__(self, parent, title, prompt, items, on_selected=None, reload_callback=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x350")
        self.on_selected = on_selected
        self.reload_callback = reload_callback
        
        top_frame = tk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(top_frame, text=prompt).pack(side=tk.LEFT)
        
        if reload_callback:
            self.show_sys_var = tk.BooleanVar(value=parent.app_config.get("show_system_apps", False))
            tk.Checkbutton(top_frame, text="Show System Apps", variable=self.show_sys_var, 
                           command=self.trigger_reload).pack(side=tk.RIGHT)
        
        # Filter entry
        self.filter_var = tk.StringVar()
        self.filter_var.trace("w", self.update_list)
        tk.Entry(self, textvariable=self.filter_var).pack(fill=tk.X, padx=10, pady=5)
        
        self.items = items
        
        # Listbox with scrollbar
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        self.update_list()
        
        self.listbox.bind("<Double-Button-1>", self.on_select)
        
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=10)
        tk.Button(btn_frame, text="Select", command=self.on_select).pack(side=tk.RIGHT, padx=10)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)
        
        self.transient(parent)
        self.grab_set()
        
    def trigger_reload(self):
        if self.reload_callback:
            self.items = self.reload_callback(self.show_sys_var.get())
            self.update_list()
        
    def update_list(self, *args):
        search = self.filter_var.get().lower()
        self.listbox.delete(0, tk.END)
        for item in self.items:
            if search in item.lower():
                self.listbox.insert(tk.END, item)
                
    def on_select(self, event=None):
        selection = self.listbox.curselection()
        if selection:
            result = self.listbox.get(selection[0])
            if self.on_selected:
                self.on_selected(result)
            self.destroy()

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Advanced Settings")
        self.geometry("450x350")
        self.parent = parent
        
        # Load working copy of config
        self.cfg = parent.app_config.copy()
        
        main_frame = tk.Frame(self, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Wait option
        self.wait_var = tk.BooleanVar(value=self.cfg.get("wait_for_manual_changes", False))
        tk.Checkbutton(main_frame, text="Wait for manual changes (pauses patching to let you edit files)", 
                       variable=self.wait_var).pack(anchor=tk.W, pady=(0,10))
                       
        # Custom Certificate
        tk.Label(main_frame, text="Custom Certificate (.pem / .der) for Network Security Config:").pack(anchor=tk.W)
        cert_frame = tk.Frame(main_frame)
        cert_frame.pack(fill=tk.X, pady=(0,15))
        
        self.cert_var = tk.StringVar(value=self.cfg.get("custom_certificate_path", ""))
        tk.Entry(cert_frame, textvariable=self.cert_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(cert_frame, text="Browse", command=self.browse_cert).pack(side=tk.LEFT, padx=5)
        tk.Button(cert_frame, text="Clear", command=lambda: self.cert_var.set("")).pack(side=tk.LEFT)
        
        # Maps API Keys
        tk.Label(main_frame, text="Google Maps API Keys:").pack(anchor=tk.W)
        maps_frame = tk.Frame(main_frame)
        maps_frame.pack(fill=tk.X)
        
        self.maps_combo = ttk.Combobox(maps_frame, state="readonly", width=25)
        self.maps_combo.pack(side=tk.LEFT, padx=(0,5))
        self.refresh_maps_combo()
        
        tk.Button(maps_frame, text="Add", command=self.add_map_key).pack(side=tk.LEFT, padx=2)
        tk.Button(maps_frame, text="Remove", command=self.remove_map_key).pack(side=tk.LEFT, padx=2)
        
        # Bottom buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=15)
        tk.Button(btn_frame, text="Save", command=self.save, width=10).pack(side=tk.RIGHT)
        tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10).pack(side=tk.RIGHT, padx=10)
        
        self.transient(parent)
        self.grab_set()
        
    def browse_cert(self):
        filename = filedialog.askopenfilename(
            title="Select Certificate",
            filetypes=(("Certificates", "*.pem *.der"), ("All files", "*.*"))
        )
        if filename:
            self.cert_var.set(filename)
            
    def refresh_maps_combo(self):
        keys = self.cfg.get("maps_api_keys", {})
        values = list(keys.keys())
        values.insert(0, "") # Option to have no key selected
        self.maps_combo['values'] = values
        
        selected = self.cfg.get("selected_maps_api_key_name", "")
        if selected in values:
            self.maps_combo.set(selected)
        else:
            self.maps_combo.set("")
            
    def add_map_key(self):
        name = simpledialog.askstring("Name", "Enter a display name for this key:", parent=self)
        if not name: return
        key_val = simpledialog.askstring("API Key", "Enter the Google Maps API Key:", parent=self)
        if not key_val: return
        
        if "maps_api_keys" not in self.cfg:
            self.cfg["maps_api_keys"] = {}
            
        self.cfg["maps_api_keys"][name] = key_val.strip()
        self.cfg["selected_maps_api_key_name"] = name
        self.refresh_maps_combo()
        
    def remove_map_key(self):
        selected = self.maps_combo.get()
        if selected and selected in self.cfg.get("maps_api_keys", {}):
            del self.cfg["maps_api_keys"][selected]
            if self.cfg.get("selected_maps_api_key_name") == selected:
                self.cfg["selected_maps_api_key_name"] = ""
            self.refresh_maps_combo()
            
    def save(self):
        self.cfg["wait_for_manual_changes"] = self.wait_var.get()
        self.cfg["custom_certificate_path"] = self.cert_var.get()
        self.cfg["selected_maps_api_key_name"] = self.maps_combo.get()
        
        # Save to parent and disk
        self.parent.app_config = self.cfg
        import config
        config.save_config(self.cfg)
        self.destroy()

def global_exception_handler(exc_type, exc_value, exc_traceback):
    import traceback
    from datetime import datetime
    
    # Ignore keyboard interrupts
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    try:
        with open("crash.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- Crash at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f.write(error_msg)
            
        messagebox.showerror("Fatal Error", f"An unexpected error occurred. A crash report was saved to crash.log.\n\n{exc_value}")
    except Exception:
        pass # If we can't even write the log, just fail silently
        
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

if __name__ == "__main__":
    sys.excepthook = global_exception_handler
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
