"""
Smart system checker that detects system state and available options
"""

import subprocess
import os
from pathlib import Path
import shutil


class SystemChecker:
    """Intelligent system state checker"""

    def __init__(self):
        self.last_result = None

    def check_all(self):
        """Perform comprehensive system check"""
        result = {
            "waydroid_installed": self.is_waydroid_installed(),
            "waydroid_initialized": self.is_waydroid_initialized(),
            "kernel_modules_ok": self.check_kernel_modules(),
            "system_compatible": self.is_system_compatible(),
        }

        self.last_result = result
        return result

    def get_last_result(self):
        """Get last check result"""
        return self.last_result

    def is_waydroid_installed(self):
        """Check if Waydroid is installed"""
        return shutil.which("waydroid") is not None

    def is_waydroid_initialized(self):
        """Check if Waydroid has been initialized"""
        waydroid_data = Path("/var/lib/waydroid")
        return waydroid_data.exists() and any(waydroid_data.iterdir())

    def check_kernel_modules(self):
        """Check if required kernel modules are available"""
        modules = ["binder_linux", "ashmem_linux"]

        for module in modules:
            try:
                result = subprocess.run(
                    ["modprobe", "-n", module], capture_output=True, timeout=5
                )
                if result.returncode != 0:
                    return False
            except (subprocess.SubprocessError, OSError):
                return False

        return True

    def is_system_compatible(self):
        """Check if system is Arch-based"""
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    content = f.read().lower()
                    return "arch" in content or "parch" in content
        except OSError:
            pass

        return False
