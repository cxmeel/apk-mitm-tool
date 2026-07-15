import subprocess
import os
import platform
import threading

class PatchTask:
    def __init__(self, apk_path, executor_cmd, config, log_callback=None, done_callback=None):
        self.apk_path = apk_path
        self.executor_cmd = executor_cmd
        self.config = config
        self.log_callback = log_callback
        self.done_callback = done_callback
        
        self.process = None
        self.thread = None
        self.is_cancelled = False
        
    def start(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
    def cancel(self):
        self.is_cancelled = True
        if self.process:
            try:
                if platform.system() == 'Windows':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    self.process.terminate()
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"\nFailed to cancel process: {e}\n")
                    
    def resume(self):
        """Sends a newline to stdin to resume if waiting."""
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write("\n")
                self.process.stdin.flush()
                if self.log_callback:
                    self.log_callback("\n[Resumed process via user input]\n")
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"\nFailed to resume process: {e}\n")

    def _run(self):
        use_shell = platform.system() == 'Windows'
        
        cmd = self.executor_cmd + ["apk-mitm@latest", self.apk_path]
        
        # Apply config flags
        if self.config.get("wait_for_manual_changes"):
            cmd.append("--wait")
            
        cert_path = self.config.get("custom_certificate_path")
        if cert_path and os.path.exists(cert_path):
            cmd.extend(["--certificate", cert_path])
            
        selected_api_key_name = self.config.get("selected_maps_api_key_name")
        maps_keys = self.config.get("maps_api_keys", {})
        if selected_api_key_name and selected_api_key_name in maps_keys:
            cmd.extend(["--maps-api-key", maps_keys[selected_api_key_name]])
            
        if self.log_callback:
            self.log_callback(f"> {' '.join(cmd)}\n")
            
        kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'stdin': subprocess.PIPE,
            'text': True,
            'bufsize': 1, # line buffered
            'universal_newlines': True
        }
        
        if platform.system() == 'Windows':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
        try:
            self.process = subprocess.Popen(cmd, shell=use_shell, **kwargs)
            
            # Read line by line and stream to callback
            for line in iter(self.process.stdout.readline, ''):
                if self.log_callback:
                    # Remove ANSI escape codes that might come from npm/apk-mitm
                    import re
                    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                    clean_line = ansi_escape.sub('', line)
                    self.log_callback(clean_line)
                    
            self.process.stdout.close()
            return_code = self.process.wait()
            
            if self.is_cancelled:
                if self.log_callback:
                    self.log_callback(f"\nPatching was cancelled by the user.\n")
                if self.done_callback:
                    self.done_callback(False, None)
                return
            
            # apk-mitm outputs to `<filename>-patched.apk`
            dirname = os.path.dirname(self.apk_path)
            basename = os.path.basename(self.apk_path)
            name, ext = os.path.splitext(basename)
            expected_out = os.path.join(dirname, f"{name}-patched{ext}")
            
            if return_code == 0:
                if self.log_callback:
                    self.log_callback(f"\nPatching successful! Output should be at:\n{expected_out}\n")
                if self.done_callback:
                    self.done_callback(True, expected_out)
            else:
                if self.log_callback:
                    self.log_callback(f"\nPatching failed with return code {return_code}\n")
                if self.done_callback:
                    self.done_callback(False, None)
                    
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"\nException running apk-mitm: {str(e)}\n")
            if self.done_callback:
                self.done_callback(False, None)
