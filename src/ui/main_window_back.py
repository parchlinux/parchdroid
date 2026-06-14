"""
Main Window - Beautiful GNOME-style UI
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

# Try different VTE versions
try:
    gi.require_version('Vte', '3.91')
except ValueError:
    try:
        gi.require_version('Vte', '2.91')
    except ValueError:
        pass

from gi.repository import Gtk, Adw, GLib, Gio

try:
    from gi.repository import Vte, Pango
    HAS_VTE = True
except ImportError:
    HAS_VTE = False
    print("Warning: VTE not available, terminal output will be limited")

import threading

from core.system_check import SystemChecker
from core.installer import WaydroidInstaller

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_default_size(900, 700)
        self.set_title("Android App Support")
        
        self.system_checker = SystemChecker()
        self.installer = None
        self.is_installing = False
        
        self.setup_ui()
        
        # Run system check automatically
        GLib.timeout_add(100, self.perform_system_check)
        
    def setup_ui(self):
        """Setup the main UI"""
        # Toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        
        # Breakpoint for responsive design
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 500sp"))
        self.add_breakpoint(breakpoint)
        
        # Header Bar
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        
        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu = Gio.Menu()
        menu.append("About", "win.about")
        menu.append("Quit", "app.quit")
        menu_button.set_menu_model(menu)
        menu_button.set_primary(True)
        header.pack_end(menu_button)
        
        # Toolbar view
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        
        # Main stack for different views
        self.main_stack = Adw.ViewStack()
        self.main_stack.set_vexpand(True)
        
        # === CHECKING VIEW ===
        self.checking_page = self.create_checking_view()
        self.main_stack.add_named(self.checking_page, "checking")
        
        # === WELCOME VIEW ===
        self.welcome_page = self.create_welcome_view()
        self.main_stack.add_named(self.welcome_page, "welcome")
        
        # === READY VIEW (Waydroid installed) ===
        self.ready_page = self.create_ready_view()
        self.main_stack.add_named(self.ready_page, "ready")
        
        # === INSTALLATION VIEW ===
        self.install_page = self.create_install_view()
        self.main_stack.add_named(self.install_page, "install")
        
        toolbar_view.set_content(self.main_stack)
        self.toast_overlay.set_child(toolbar_view)
        self.set_content(self.toast_overlay)
        
        # Setup actions
        self.setup_actions()
        
        # Show checking view initially
        self.main_stack.set_visible_child_name("checking")
        
    def create_checking_view(self):
        """Create elegant checking view"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_valign(Gtk.Align.CENTER)
        box.set_vexpand(True)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_halign(Gtk.Align.CENTER)
        
        # Animated spinner
        spinner = Gtk.Spinner()
        spinner.set_size_request(64, 64)
        spinner.start()
        content.append(spinner)
        
        # Title
        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Checking Your System</span>")
        content.append(title)
        
        # Subtitle
        subtitle = Gtk.Label()
        subtitle.set_text("Detecting configuration and status...")
        subtitle.add_css_class("dim-label")
        content.append(subtitle)
        
        clamp.set_child(content)
        box.append(clamp)
        
        return box
        
    def create_welcome_view(self):
        """Create beautiful welcome view for new installations"""
        clamp = Adw.Clamp()
        clamp.set_maximum_size(700)
        clamp.set_margin_top(12)
        clamp.set_margin_bottom(12)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=36)
        main_box.set_valign(Gtk.Align.CENTER)
        
        # Hero section
        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        hero_box.set_halign(Gtk.Align.CENTER)
        
        # Large icon
        icon = Gtk.Image.new_from_icon_name("phone-symbolic")
        icon.set_pixel_size(128)
        icon.add_css_class("accent")
        hero_box.append(icon)
        
        # Title
        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>Android App Support</span>")
        title.set_margin_top(12)
        hero_box.append(title)
        
        # Description
        desc = Gtk.Label()
        desc.set_text("Run Android applications natively on your Parch Linux system")
        desc.add_css_class("dim-label")
        desc.set_wrap(True)
        desc.set_justify(Gtk.Justification.CENTER)
        hero_box.append(desc)
        
        main_box.append(hero_box)
        
        # Feature cards in a beautiful layout
        features_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # System status card
        self.status_card = Adw.PreferencesGroup()
        self.status_card.set_title("System Status")
        self.status_card.set_description("Current configuration detected on your system")
        
        # Repository row
        self.repo_row = Adw.ActionRow()
        self.repo_row.set_title("Installation Source")
        repo_icon = Gtk.Image.new_from_icon_name("folder-download-symbolic")
        self.repo_row.add_prefix(repo_icon)
        self.status_card.add(self.repo_row)
        
        # Kernel modules row
        self.kernel_row = Adw.ActionRow()
        self.kernel_row.set_title("Kernel Support")
        kernel_icon = Gtk.Image.new_from_icon_name("application-x-firmware-symbolic")
        self.kernel_row.add_prefix(kernel_icon)
        self.status_card.add(self.kernel_row)
        
        features_box.append(self.status_card)
        
        # Action card
        action_card = Adw.PreferencesGroup()
        action_card.set_title("Get Started")
        
        # Install button in a prominent card
        install_row = Adw.ActionRow()
        install_row.set_title("Install Waydroid")
        install_row.set_subtitle("Set up Android application support on your system")
        install_icon = Gtk.Image.new_from_icon_name("emblem-downloads-symbolic")
        install_row.add_prefix(install_icon)
        
        self.install_button = Gtk.Button()
        self.install_button.set_label("Install")
        self.install_button.set_valign(Gtk.Align.CENTER)
        self.install_button.add_css_class("suggested-action")
        self.install_button.add_css_class("pill")
        self.install_button.connect("clicked", self.on_install_clicked)
        install_row.add_suffix(self.install_button)
        install_row.set_activatable_widget(self.install_button)
        
        action_card.add(install_row)
        features_box.append(action_card)
        
        main_box.append(features_box)
        
        clamp.set_child(main_box)
        return clamp
        
    def create_ready_view(self):
        """Create view for when Waydroid is installed"""
        clamp = Adw.Clamp()
        clamp.set_maximum_size(700)
        clamp.set_margin_top(12)
        clamp.set_margin_bottom(12)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        
        # Status banner
        banner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        banner_box.set_halign(Gtk.Align.CENTER)
        banner_box.set_margin_bottom(12)
        
        success_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        success_icon.set_pixel_size(64)
        success_icon.add_css_class("success")
        banner_box.append(success_icon)
        
        status_label = Gtk.Label()
        status_label.set_markup("<span size='x-large' weight='bold'>Waydroid is Ready</span>")
        banner_box.append(status_label)
        
        main_box.append(banner_box)
        
        # Quick actions card
        quick_actions = Adw.PreferencesGroup()
        quick_actions.set_title("Quick Actions")
        quick_actions.set_description("Manage your Android environment")
        
        # Initialize row
        self.init_row = Adw.ActionRow()
        self.init_row.set_title("Initialize System Images")
        self.init_row.set_subtitle("Download Android system files (required first time)")
        init_icon = Gtk.Image.new_from_icon_name("emblem-synchronizing-symbolic")
        self.init_row.add_prefix(init_icon)
        
        self.init_button = Gtk.Button()
        self.init_button.set_label("Initialize")
        self.init_button.set_valign(Gtk.Align.CENTER)
        self.init_button.connect("clicked", self.on_initialize_clicked)
        self.init_row.add_suffix(self.init_button)
        self.init_row.set_activatable_widget(self.init_button)
        
        quick_actions.add(self.init_row)
        
        # Launch row
        self.launch_row = Adw.ActionRow()
        self.launch_row.set_title("Launch Waydroid")
        self.launch_row.set_subtitle("Start the Android environment")
        launch_icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
        self.launch_row.add_prefix(launch_icon)
        
        self.launch_button = Gtk.Button()
        self.launch_button.set_label("Launch")
        self.launch_button.set_valign(Gtk.Align.CENTER)
        self.launch_button.add_css_class("suggested-action")
        self.launch_button.connect("clicked", self.on_launch_clicked)
        self.launch_row.add_suffix(self.launch_button)
        self.launch_row.set_activatable_widget(self.launch_button)
        
        quick_actions.add(self.launch_row)
        
        main_box.append(quick_actions)
        
        # System info card
        info_card = Adw.PreferencesGroup()
        info_card.set_title("System Information")
        
        # Status rows
        self.waydroid_status_row = Adw.ActionRow()
        self.waydroid_status_row.set_title("Waydroid Status")
        status_icon = Gtk.Image.new_from_icon_name("emblem-default-symbolic")
        self.waydroid_status_row.add_prefix(status_icon)
        info_card.add(self.waydroid_status_row)
        
        self.modules_status_row = Adw.ActionRow()
        self.modules_status_row.set_title("Kernel Modules")
        modules_icon = Gtk.Image.new_from_icon_name("application-x-firmware-symbolic")
        self.modules_status_row.add_prefix(modules_icon)
        info_card.add(self.modules_status_row)
        
        main_box.append(info_card)
        
        # Help card
        help_card = Adw.PreferencesGroup()
        help_card.set_title("Need Help?")
        
        help_row = Adw.ActionRow()
        help_row.set_title("View Documentation")
        help_row.set_subtitle("Learn more about using Waydroid")
        help_icon = Gtk.Image.new_from_icon_name("help-browser-symbolic")
        help_row.add_prefix(help_icon)
        
        help_button = Gtk.Button()
        help_button.set_icon_name("go-next-symbolic")
        help_button.set_valign(Gtk.Align.CENTER)
        help_button.add_css_class("flat")
        help_row.add_suffix(help_button)
        help_row.set_activatable_widget(help_button)
        
        help_card.add(help_row)
        main_box.append(help_card)
        
        clamp.set_child(main_box)
        return clamp
        
    def create_install_view(self):
        """Create modern installation progress view"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Content with clamp for nice centering
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_vexpand(True)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        
        # Status section
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # Status with icon
        status_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.status_spinner = Gtk.Spinner()
        self.status_spinner.set_size_request(24, 24)
        self.status_spinner.start()
        status_header.append(self.status_spinner)
        
        self.install_status = Gtk.Label()
        self.install_status.set_markup("<span size='large' weight='bold'>Preparing installation...</span>")
        self.install_status.set_xalign(0)
        self.install_status.set_hexpand(True)
        status_header.append(self.install_status)
        
        status_box.append(status_header)
        
        # Progress bar with modern styling
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(False)
        self.progress_bar.pulse()
        self.progress_bar.add_css_class("osd")
        status_box.append(self.progress_bar)
        
        content.append(status_box)
        
        # Terminal section with nice frame
        terminal_frame = Gtk.Frame()
        terminal_frame.set_vexpand(True)
        terminal_frame.add_css_class("view")
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        # scrolled.set_hscrollbar_policy(Gtk.PolicyType.AUTOMATIC)
        # scrolled.set_vscrollbar_policy(Gtk.PolicyType.AUTOMATIC)
        
        if HAS_VTE:
            self.terminal = Vte.Terminal()
            self.terminal.set_font(Pango.FontDescription("Monospace 11"))
            self.terminal.set_scroll_on_output(True)
            self.terminal.set_scrollback_lines(10000)
            scrolled.set_child(self.terminal)
        else:
            # Fallback to TextView
            self.terminal_view = Gtk.TextView()
            self.terminal_view.set_editable(False)
            self.terminal_view.set_monospace(True)
            self.terminal_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            self.terminal_view.set_left_margin(12)
            self.terminal_view.set_right_margin(12)
            self.terminal_view.set_top_margin(12)
            self.terminal_view.set_bottom_margin(12)
            self.terminal_buffer = self.terminal_view.get_buffer()
            scrolled.set_child(self.terminal_view)
            self.terminal = None
        
        terminal_frame.set_child(scrolled)
        content.append(terminal_frame)
        
        # Button bar
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)
        
        self.back_button = Gtk.Button(label="Done")
        self.back_button.set_visible(False)
        self.back_button.add_css_class("suggested-action")
        self.back_button.connect("clicked", self.on_done_clicked)
        button_box.append(self.back_button)
        
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.connect("clicked", self.on_cancel_install)
        button_box.append(self.cancel_button)
        
        content.append(button_box)
        
        clamp.set_child(content)
        box.append(clamp)
        
        return box
        
    def perform_system_check(self):
        """Perform system check in background"""
        def check_thread():
            result = self.system_checker.check_all()
            GLib.idle_add(self.on_system_check_complete, result)
            
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
        return False
        
    def on_system_check_complete(self, result):
        """Handle system check completion"""
        # Determine which view to show
        if result['waydroid_installed']:
            # Show ready view
            self.update_ready_view(result)
            self.main_stack.set_visible_child_name("ready")
        else:
            # Show welcome view
            self.update_welcome_view(result)
            self.main_stack.set_visible_child_name("welcome")
        
        return False
        
    def update_welcome_view(self, result):
        """Update welcome view with system info"""
        # Update repository info
        if result['chaotic_available']:
            self.repo_row.set_subtitle("Chaotic-AUR (fast installation)")
            self.install_button.set_sensitive(True)
        elif result['aur_helper']:
            self.repo_row.set_subtitle(f"AUR via {result['aur_helper']} (build from source)")
            self.install_button.set_sensitive(True)
        else:
            self.repo_row.set_subtitle("Not available - install an AUR helper")
            self.install_button.set_sensitive(False)
            
        # Update kernel info
        if result['kernel_modules_ok']:
            self.kernel_row.set_subtitle("All required modules available")
        else:
            self.kernel_row.set_subtitle("Some modules missing - installation will proceed")
            
    def update_ready_view(self, result):
        """Update ready view with system info"""
        # Update status
        if result['waydroid_initialized']:
            self.waydroid_status_row.set_subtitle("Initialized and ready")
            self.init_row.set_visible(False)
            self.launch_row.set_visible(True)
        else:
            self.waydroid_status_row.set_subtitle("Installed but not initialized")
            self.init_row.set_visible(True)
            self.launch_row.set_visible(False)
            
        # Update modules status
        if result['kernel_modules_ok']:
            self.modules_status_row.set_subtitle("All modules loaded")
        else:
            self.modules_status_row.set_subtitle("Some modules unavailable")
            
    def on_install_clicked(self, button):
        """Handle install button click"""
        result = self.system_checker.get_last_result()
        
        # Determine installation source
        if result['chaotic_available']:
            source = 'chaotic'
            source_name = "Chaotic-AUR"
        elif result['aur_helper']:
            source = 'aur'
            source_name = "AUR"
        else:
            self.show_toast("No installation source available")
            return
            
        # Show elegant confirmation
        dialog = Adw.MessageDialog(transient_for=self)
        dialog.set_heading("Install Waydroid?")
        dialog.set_body(f"Waydroid will be installed from {source_name}.\n\nThis process may take a few minutes.")
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("install")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", lambda d, r: self.start_installation(source) if r == "install" else None)
        dialog.present()
        
    def start_installation(self, source):
        """Start the installation process"""
        self.is_installing = True
        self.main_stack.set_visible_child_name("install")
        
        if HAS_VTE and self.terminal:
            self.terminal.reset(True, True)
        else:
            self.terminal_buffer.set_text("")
            
        self.back_button.set_visible(False)
        self.cancel_button.set_visible(True)
        self.status_spinner.start()
        
        # Create installer
        self.installer = WaydroidInstaller()
        self.installer.connect('output', self.on_installer_output)
        self.installer.connect('status', self.on_installer_status)
        self.installer.connect('progress', self.on_installer_progress)
        self.installer.connect('completed', self.on_installer_completed)
        self.installer.connect('password-required', self.on_password_required)
        
        # Start installation thread
        thread = threading.Thread(target=self.installer.install, args=(source,), daemon=True)
        thread.start()
        
    def on_installer_output(self, installer, text):
        """Handle installer output"""
        def update():
            if HAS_VTE and self.terminal:
                self.terminal.feed(text.encode('utf-8'))
            else:
                end_iter = self.terminal_buffer.get_end_iter()
                self.terminal_buffer.insert(end_iter, text)
                # Auto-scroll to end
                mark = self.terminal_buffer.get_insert()
                self.terminal_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        GLib.idle_add(update)
        
    def on_installer_status(self, installer, status):
        """Handle installer status update"""
        GLib.idle_add(lambda: self.install_status.set_markup(f"<span size='large' weight='bold'>{status}</span>"))
        
    def on_installer_progress(self, installer, fraction):
        """Handle installer progress"""
        def update():
            if fraction < 0:
                self.progress_bar.pulse()
            else:
                self.progress_bar.set_fraction(fraction)
                self.progress_bar.set_show_text(True)
        GLib.idle_add(update)
        
    def on_installer_completed(self, installer, success):
        """Handle installation completion"""
        def finalize():
            self.is_installing = False
            self.cancel_button.set_visible(False)
            self.back_button.set_visible(True)
            self.status_spinner.stop()
            
            if success:
                self.install_status.set_markup("<span size='large' weight='bold'>✓ Installation Complete!</span>")
                self.progress_bar.set_fraction(1.0)
                self.show_toast("Waydroid installed successfully")
            else:
                self.install_status.set_markup("<span size='large' weight='bold'>✗ Installation Failed</span>")
                self.show_toast("Installation failed. Check the log for details.")
                
        GLib.idle_add(finalize)
        
    def on_password_required(self, installer):
        """Handle password request with beautiful dialog"""
        def ask():
            dialog = Adw.MessageDialog(transient_for=self)
            dialog.set_heading("Authentication Required")
            dialog.set_body("Administrator privileges are required to install system packages.")
            
            # Password entry in a nice box
            entry_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            entry_box.set_margin_top(12)
            
            entry = Gtk.PasswordEntry()
            entry.set_show_peek_icon(True)
            entry.set_placeholder_text("Enter your password")
            entry_box.append(entry)
            
            dialog.set_extra_child(entry_box)
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("auth", "Authenticate")
            dialog.set_response_appearance("auth", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("auth")
            
            def on_response(d, r):
                if r == "auth":
                    self.installer.provide_password(entry.get_text())
                else:
                    self.installer.cancel()
                    
            dialog.connect("response", on_response)
            entry.connect("activate", lambda e: dialog.response("auth"))
            dialog.present()
            
        GLib.idle_add(ask)
        
    def on_cancel_install(self, button):
        """Cancel installation"""
        if self.installer:
            self.installer.cancel()
            
    def on_done_clicked(self, button):
        """Go back after installation"""
        # Refresh system check
        self.main_stack.set_visible_child_name("checking")
        GLib.timeout_add(500, self.perform_system_check)
        
    def on_initialize_clicked(self, button):
        """Handle initialize button click"""
        self.show_toast("Initialization feature coming soon")
        
    def on_launch_clicked(self, button):
        """Handle launch button click"""
        self.show_toast("Launch feature coming soon")
        
    def show_toast(self, message):
        """Show a toast notification"""
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)
        
    def setup_actions(self):
        """Setup window actions"""
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)
        
    def on_about(self, action, param):
        """Show beautiful about dialog"""
        about = Adw.AboutWindow(transient_for=self)
        about.set_application_name("Android App Support")
        about.set_application_icon("phone")
        about.set_developer_name("Parch Linux")
        about.set_version("1.0.0")
        about.set_comments("Install and manage Waydroid for Android app support on Parch Linux")
        about.set_website("https://parchlinux.com")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.add_credit_section("Contributors", ["Parch Linux Team"])
        about.present()
