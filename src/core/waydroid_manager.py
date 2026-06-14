"""
Waydroid Manager - Handles initialization, status, and operations
"""
import subprocess
import time
import re
from pathlib import Path
from gi.repository import GObject
import pexpect
import configparser
import shutil

class WaydroidManager(GObject.Object):
    """Manages Waydroid operations"""
    __gsignals__ = {
        'output': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        'status': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
        'progress': (GObject.SIGNAL_RUN_FIRST, None, (float,)),
        'completed': (GObject.SIGNAL_RUN_FIRST, None, (bool,)),
        'password-required': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__()
        self.process = None
        self.cancelled = False
        self.password = None
        self.config_path = Path('/var/lib/waydroid/waydroid.cfg')

    # ----------------------------- Logging -----------------------------
    def log(self, message):
        """Log a message"""
        self.emit('output', f"{message}\n")

    def set_status(self, status):
        """Update status"""
        self.emit('status', status)

    def set_progress(self, fraction):
        """Update progress"""
        self.emit('progress', fraction)

    # ----------------------------- Config Parsing -----------------------------
    def load_config(self):
        """Load and parse waydroid.cfg"""
        if not self.config_path.exists():
            return {}

        config = configparser.ConfigParser()
        config.read(self.config_path)
        return {section: dict(config.items(section)) for section in config.sections()}

    # ----------------------------- Status ------------------------------
    def get_status(self, include_props=False):
        """Get Waydroid status information"""
        config = self.load_config()
        status = {
            'installed': self.is_installed(),
            'initialized': self.is_initialized(),
            'session_running': self.is_session_running(),
            'container_running': self.is_container_running(),
            'has_gapps': self.has_gapps(config),
            'android_version': self.get_android_version(),
            'system_image': self.get_system_image(config),
            'ip_address': self.get_ip_address(),
            'arch': config.get('waydroid', {}).get('arch', 'Unknown'),
            'vendor_type': config.get('waydroid', {}).get('vendor_type', 'Unknown'),
            'images_path': config.get('waydroid', {}).get('images_path', 'Unknown'),
            'system_ota': config.get('waydroid', {}).get('system_ota', 'Unknown'),
            'vendor_ota': config.get('waydroid', {}).get('vendor_ota', 'Unknown'),
            'waydroid_props': self.get_waydroid_props() if include_props else {},
        }
        # Logic for graying out images button: if images_path is 'Unknown' or not default, UI can use this
        status['images_available'] = status['images_path'] != 'Unknown' and Path(status['images_path']).exists()
        return status

    def is_installed(self):
        """Check if Waydroid is installed"""
        return shutil.which('waydroid') is not None

    def is_initialized(self):
        """Check if Waydroid is initialized"""
        overlay = Path('/var/lib/waydroid/overlay')
        return overlay.exists() and any(overlay.iterdir()) and self.config_path.exists()

    def is_session_running(self):
        """Check if Waydroid session is running"""
        try:
            result = subprocess.run(['waydroid', 'status'], capture_output=True, text=True, timeout=5)
            return 'Session' in result.stdout and 'RUNNING' in result.stdout
        except Exception:
            return False

    def is_container_running(self):
        """Check if Waydroid container is running"""
        try:
            result = subprocess.run(['systemctl', 'is-active', 'waydroid-container'],
                                    capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def has_gapps(self, config=None):
        """Check if GApps are installed"""
        if config is None:
            config = self.load_config()
        if 'waydroid' in config and 'system_ota' in config['waydroid']:
            return 'GAPPS' in config['waydroid']['system_ota'].upper()
        gms_path = Path('/var/lib/waydroid/overlay/vendor/etc/permissions/privapp-permissions-google.xml')
        return gms_path.exists()

    def get_android_version(self):
        """Get Android version"""
        try:
            prop_file = Path('/var/lib/waydroid/waydroid_base.prop')
            if prop_file.exists():
                with open(prop_file, 'r') as f:
                    for line in f:
                        if 'ro.build.version.release' in line:
                            return line.split('=')[1].strip()
        except Exception:
            pass
        return "Unknown"

    def get_system_image(self, config=None):
        """Get Waydroid system image name"""
        if config is None:
            config = self.load_config()
        if 'waydroid' in config and 'system_ota' in config['waydroid']:
            url = config['waydroid']['system_ota']
            parts = url.split('/')
            if parts:
                variant = parts[-1].replace('.json', '').strip()
                arch = parts[-2].split('_')[-1] if len(parts) > 1 and '_' in parts[-2] else ''
                base = 'LineageOS' if 'lineage' in url else 'Unknown'
                return f"{base} {arch} {variant}"
        # Fallback
        try:
            result = subprocess.run(['waydroid', 'status'], capture_output=True, text=True, timeout=5)
            match = re.search(r'System image:\s*(.+)', result.stdout)
            if match:
                img = match.group(1).strip()
                if "unknown" not in img.lower():
                    return img
        except Exception:
            pass
        return "Unknown"

    def get_ip_address(self):
        """Get Waydroid IP address"""
        try:
            result = subprocess.run(['waydroid', 'status'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'IP address' in line:
                    return line.split(':')[1].strip()
        except Exception:
            pass
        return "Not available"

    def get_waydroid_props(self):
        """Get all persist.waydroid.* properties"""
        props = {}
        was_running = self.is_container_running()
        try:
            if not was_running:
                self.log("Starting Waydroid container to fetch properties...")
                if not self.run_with_sudo(['systemctl', 'start', 'waydroid-container']):
                    return {}
                time.sleep(5)  # Give time for container to start
            result = subprocess.run(['waydroid', 'shell', 'getprop'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith('[') and ']:' in line:
                        key = line.split(']:', 1)[0][1:].strip()
                        value = line.split(']:', 1)[1][2:-1].strip() if len(line.split(']:', 1)) > 1 else ''
                        if key.startswith('persist.waydroid.'):
                            props[key] = value
        except Exception as e:
            self.log(f"✗ Error getting Waydroid props: {e}")
        finally:
            if not was_running:
                self.log("Stopping Waydroid container after fetching properties...")
                self.run_with_sudo(['systemctl', 'stop', 'waydroid-container'])
        return props

    # ----------------------------- Core Ops -----------------------------
    def initialize(self, image_type='vanilla', force=False):
        """Initialize Waydroid with specific image type"""
        self.cancelled = False
        try:
            self.set_status(f"Initializing Waydroid ({image_type})...")
            self.set_progress(-1)
            if image_type == 'vanilla':
                self.log("Initializing Waydroid with vanilla Android images (no Google apps).")
            else:
                self.log("Initializing Waydroid with GApps (includes Play Store).")
            cmd = ['waydroid', 'init']
            if force:
                cmd.append('-f')
            if image_type == 'gapps':
                cmd.extend(['-s', 'GAPPS'])
            if not self.run_with_sudo(cmd):
                self.emit('completed', False)
                return
            self.set_progress(1.0)
            self.log("✓ Waydroid initialized successfully!")
            self.emit('completed', True)
        except Exception as e:
            self.log(f"✗ Initialization failed: {e}")
            self.emit('completed', False)

    def reset(self, image_type='vanilla'):
        """Delete and re-initialize Waydroid (advanced operation)"""
        self.cancelled = False
        try:
            self.set_status("Resetting Waydroid...")
            self.set_progress(-1)
            self.log("Stopping Waydroid...")
            self.stop_session()
            self.log("Re-initializing Waydroid with force...")
            self.initialize(image_type, force=True)
        except Exception as e:
            self.log(f"✗ Reset failed: {e}")
            self.emit('completed', False)

    def start_session(self):
        """Start Waydroid session"""
        self.cancelled = False
        try:
            self.set_status("Starting Waydroid session...")
            self.set_progress(-1)
            if not self.run_with_sudo(['systemctl', 'start', 'waydroid-container']):
                self.emit('completed', False)
                return
            time.sleep(2)
            result = subprocess.run(['waydroid', 'session', 'start'],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode == 0 or 'running' in result.stdout.lower():
                self.log("✓ Waydroid session started successfully!")
                self.set_progress(1.0)
                self.emit('completed', True)
            else:
                self.log(f"✗ Failed to start session: {result.stderr}")
                self.emit('completed', False)
        except Exception as e:
            self.log(f"✗ Error starting session: {e}")
            self.emit('completed', False)

    def stop_session(self):
        """Stop Waydroid session"""
        try:
            self.log("Stopping Waydroid session...")
            subprocess.run(['waydroid', 'session', 'stop'], timeout=10)
            self.log("Stopping Waydroid container...")
            self.run_with_sudo(['systemctl', 'stop', 'waydroid-container'])
            self.log("✓ Waydroid stopped successfully!")
            return True
        except Exception as e:
            self.log(f"✗ Error stopping Waydroid: {e}")
            return False

    def restart_session(self):
        """Restart Waydroid session"""
        if self.stop_session():
            self.start_session()

    def launch_ui(self):
        """Launch Waydroid UI"""
        try:
            if not self.is_session_running():
                self.log("Starting Waydroid session...")
                if not self.is_container_running():
                    self.run_with_sudo(['systemctl', 'start', 'waydroid-container'])
                time.sleep(2)
                subprocess.run(['waydroid', 'session', 'start'], timeout=10)
                time.sleep(2)
            self.log("Launching Waydroid UI...")
            subprocess.Popen(['waydroid', 'show-full-ui'])
            return True
        except Exception as e:
            self.log(f"✗ Error launching UI: {e}")
            return False

    def install_apk(self, apk_path):
        """Install an APK file into Waydroid"""
        self.cancelled = False
        try:
            apk_file = Path(apk_path)
            if not apk_file.exists():
                self.log(f"✗ APK file not found: {apk_path}")
                self.emit('completed', False)
                return False
            # Show detailed Waydroid info
            status_info = f"{self.get_android_version()} ({self.get_system_image()})"
            self.set_status(f"Installing {apk_file.name} on Android {status_info}...")
            self.set_progress(-1)
            self.log(f"Installing APK: {apk_file.name}")
            # Ensure Waydroid is running
            if not self.is_session_running():
                self.log("Starting Waydroid session...")
                if not self.is_container_running():
                    self.run_with_sudo(['systemctl', 'start', 'waydroid-container'])
                time.sleep(2)
                subprocess.run(['waydroid', 'session', 'start'], timeout=10)
                time.sleep(2)
            # Install APK
            result = subprocess.run(
                ['waydroid', 'app', 'install', str(apk_file)],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                self.log(f"✓ Installed {apk_file.name}")
                self.set_progress(1.0)
                self.emit('completed', True)
                return True
            else:
                error_text = result.stderr.strip() or result.stdout.strip()
                self.log(f"✗ Failed to install {apk_file.name}: {error_text}")
                self.emit('completed', False)
                return False
        except Exception as e:
            self.log(f"⚠️ Error installing APK: {e}")
            self.emit('completed', False)
            return False

    def set_waydroid_prop(self, key, value):
        """Set a Waydroid property (advanced)"""
        self.cancelled = False
        try:
            self.set_status(f"Setting {key} to {value}...")
            self.set_progress(-1)
            cmd = ['waydroid', 'prop', 'set', key, str(value)]
            # Some properties can be set without root, others require sudo.
            # Try non-root first to reduce unnecessary auth prompts.
            if not self.run_command_interactive(cmd):
                self.log("Non-root set failed, retrying with sudo...")
                if not self.run_with_sudo(cmd):
                    self.emit('completed', False)
                    return False
            self.log(f"✓ Set {key} to {value}. Most changes require restarting the session to apply.")
            self.set_progress(1.0)
            self.emit('completed', True)
            return True
        except Exception as e:
            self.log(f"✗ Error setting property: {e}")
            self.emit('completed', False)
            return False

    # ----------------------------- Sudo Helper -----------------------------
    def run_with_sudo(self, command):
        """Run a command with sudo"""
        cmd = ['sudo'] + command
        return self.run_command_interactive(cmd)

    def run_command_interactive(self, command):
        """Run command with interactive password handling"""
        if self.cancelled:
            return False
        try:
            cmd_str = ' '.join(command)
            self.log(f"$ {cmd_str}")
            self.process = pexpect.spawn(command[0], command[1:], encoding='utf-8', timeout=300)
            password_attempts = 0
            while True:
                if self.cancelled:
                    self.process.terminate(force=True)
                    self.log("✗ Operation cancelled")
                    return False
                index = self.process.expect([
                    r'(?i)\[sudo\] password for .*:',
                    r'(?i)password:',
                    pexpect.EOF,
                    pexpect.TIMEOUT
                ], timeout=2)
                if index in [0, 1]:
                    if password_attempts >= 3:
                        self.log("✗ Too many password attempts")
                        self.process.terminate()
                        return False
                    password_attempts += 1
                    self.password = None
                    self.emit('password-required')
                    waited = 0
                    while self.password is None and waited < 600 and not self.cancelled:
                        time.sleep(0.1)
                        waited += 1
                    if self.cancelled:
                        self.process.terminate(force=True)
                        return False
                    if self.password:
                        self.process.sendline(self.password)
                        self.password = None
                    else:
                        self.log("✗ Password timeout")
                        self.process.terminate()
                        return False
                elif index == 2:  # EOF
                    break
                # Output handling
                if hasattr(self.process, 'before') and self.process.before:
                    output = self.process.before.strip()
                    if output and not output.startswith('[sudo]'):
                        self.emit('output', output + '\n')
            self.process.close()
            return self.process.exitstatus == 0
        except Exception as e:
            self.log(f"✗ Error running command: {e}")
            return False

    def provide_password(self, password):
        """Provide password for sudo"""
        self.password = password

    def cancel(self):
        """Cancel current operation"""
        self.cancelled = True
        if self.process and self.process.isalive():
            try:
                self.process.terminate(force=True)
            except Exception:
                pass
