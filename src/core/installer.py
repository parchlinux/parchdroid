"""
Smart Waydroid Installer with proper error handling and progress tracking
"""

import subprocess
import time
import shutil
from gi.repository import GObject
import pexpect

class WaydroidInstaller(GObject.Object):
    """Smart installer with automatic source selection and robust error handling"""
    
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
        self.password_event = None
        
    def log(self, message):
        """Log a message to terminal"""
        self.emit('output', f"{message}\n")
        
    def set_status(self, status):
        """Update status message"""
        self.emit('status', status)
        
    def set_progress(self, fraction):
        """Update progress (0.0-1.0, or -1 for pulse)"""
        self.emit('progress', fraction)
        
    def install(self, source='extra'):
        """Main installation method"""
        self.cancelled = False
        
        try:
            self.set_status("Preparing installation...")
            self.set_progress(-1)
            
            # Install based on source
            if source == 'aur':
                success = self.install_from_aur()
            else:
                success = self.install_from_repo()
                
            self.emit('completed', success and not self.cancelled)
            
        except Exception as e:
            self.log(f"\n✗ ERROR: {str(e)}")
            self.emit('completed', False)
            
    def install_from_repo(self):
        """Install from the configured pacman repositories"""
        self.set_status("Installing from system repositories...")
        self.log("Installing waydroid from configured pacman repositories...")
        
        # Install waydroid package
        if not self.run_with_sudo(['pacman', '-S', 'waydroid', '--noconfirm', '--needed']):
            return False
            
        self.set_progress(0.8)
        
        # Check if kernel modules are available
        self.log("\nChecking kernel modules...")
        self.check_kernel_modules()
        
        self.set_progress(1.0)
        self.log("\n✓ Waydroid installed successfully from repositories!")
        self.show_next_steps()
        
        return True
        
    def install_from_aur(self):
        """Install from AUR using helper"""
        self.set_status("Installing from AUR...")
        
        # Find AUR helper
        helpers = ['yay', 'paru', 'pikaur', 'trizen']
        aur_helper = None
        
        for helper in helpers:
            if shutil.which(helper):
                aur_helper = helper
                break
                
        if not aur_helper:
            self.log("✗ No AUR helper found!")
            self.log("Please install one of: yay, paru, pikaur, trizen")
            return False
            
        self.log(f"Using {aur_helper} to build and install from AUR...")
        self.set_status(f"Building package with {aur_helper}...")
        
        # Install using AUR helper
        cmd = [aur_helper, '-S', 'waydroid', '--noconfirm', '--needed']
        
        if not self.run_command_interactive(cmd):
            return False
            
        self.set_progress(0.8)
        self.log("\nChecking kernel modules...")
        self.check_kernel_modules()
        
        self.set_progress(1.0)
        self.log("\n✓ Waydroid built and installed successfully from AUR!")
        self.show_next_steps()
        
        return True
        
    def check_kernel_modules(self):
        """Check and inform about kernel modules"""
        modules = ['binder_linux', 'ashmem_linux']
        missing = []
        
        for module in modules:
            result = subprocess.run(
                ['modprobe', '-n', module],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                missing.append(module)
                
        if missing:
            self.log(f"⚠ Warning: Missing kernel modules: {', '.join(missing)}")
            self.log("You may need to install waydroid-support or configure modules manually.")
        else:
            self.log("✓ Required kernel modules are available")
            
    def show_next_steps(self):
        """Show next steps to user"""
        self.log("\n" + "="*60)
        self.log("NEXT STEPS:")
        self.log("="*60)
        self.log("\n1. Initialize Waydroid (downloads Android images):")
        self.log("   sudo waydroid init")
        self.log("\n2. Start Waydroid session:")
        self.log("   sudo systemctl start waydroid-container")
        self.log("   waydroid session start")
        self.log("\n3. Launch Waydroid UI:")
        self.log("   waydroid show-full-ui")
        self.log("\n" + "="*60)
        
    def run_with_sudo(self, command):
        """Run a command with sudo, handling password prompt"""
        cmd = ['sudo'] + command
        return self.run_command_interactive(cmd)
        
    def run_command_interactive(self, command):
        """Run command with interactive password handling"""
        if self.cancelled:
            return False
            
        try:
            # Join command for display
            cmd_str = ' '.join(command)
            self.log(f"$ {cmd_str}")
            
            # Spawn process
            self.process = pexpect.spawn(
                command[0],
                command[1:],
                encoding='utf-8',
                timeout=1800
            )
            
            password_attempts = 0
            max_password_attempts = 3
            
            while True:
                if self.cancelled:
                    self.process.terminate(force=True)
                    self.log("\n✗ Installation cancelled by user")
                    return False
                    
                try:
                    # Wait for various patterns
                    index = self.process.expect([
                        r'(?i)\[sudo\] password for .*:',  # Sudo password
                        r'(?i)password:',  # Generic password
                        r':: Proceed with (?:installation|download)\? \[Y/n\]',  # Pacman/AUR prompt
                        r'\[Y/n\]',  # Generic Y/n prompt
                        pexpect.EOF,
                        pexpect.TIMEOUT
                    ], timeout=2)
                    
                    if index in [0, 1]:  # Password prompt
                        if password_attempts >= max_password_attempts:
                            self.log("\n✗ Too many password attempts")
                            self.process.terminate()
                            return False
                            
                        password_attempts += 1
                        self.password = None
                        self.emit('password-required')
                        
                        # Wait for password (timeout after 60 seconds)
                        wait_time = 0
                        while self.password is None and wait_time < 600 and not self.cancelled:
                            time.sleep(0.1)
                            wait_time += 1
                            
                        if self.cancelled:
                            self.process.terminate(force=True)
                            return False
                            
                        if self.password:
                            self.process.sendline(self.password)
                            self.password = None
                        else:
                            self.log("\n✗ Password timeout")
                            self.process.terminate()
                            return False
                            
                    elif index in [2, 3]:  # Confirmation prompt
                        self.process.sendline('Y')
                        
                    elif index == 4:  # EOF - process completed
                        break
                        
                    # Read any output
                    if hasattr(self.process, 'before') and self.process.before:
                        output = self.process.before
                        if output and output.strip():
                            # Clean up the output
                            lines = output.split('\n')
                            for line in lines:
                                clean_line = line.strip()
                                if clean_line and not clean_line.startswith('[sudo]'):
                                    self.emit('output', clean_line + '\n')
                                    
                except pexpect.TIMEOUT:
                    # Read any available output during timeout
                    try:
                        output = self.process.read_nonblocking(size=4096, timeout=0)
                        if output and output.strip():
                            self.emit('output', output)
                    except:
                        pass
                        
            # Get final output
            try:
                final_output = self.process.read()
                if final_output and final_output.strip():
                    self.emit('output', final_output)
            except:
                pass
                
            # Check exit status
            self.process.close()
            
            if self.process.exitstatus == 0:
                return True
            else:
                self.log(f"\n✗ Command failed with exit code {self.process.exitstatus}")
                return False
                
        except Exception as e:
            self.log(f"\n✗ Error running command: {str(e)}")
            return False
            
    def provide_password(self, password):
        """Provide password for sudo authentication"""
        self.password = password
        
    def cancel(self):
        """Cancel the installation"""
        self.cancelled = True
        if self.process and self.process.isalive():
            try:
                self.process.terminate(force=True)
            except:
                pass
