"""
Main Window - Complete Waydroid Management UI
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
import threading
from pathlib import Path
from gettext import gettext as _
from core.system_check import SystemChecker
from core.installer import WaydroidInstaller
from core.waydroid_manager import WaydroidManager
class MainWindow(Adw.ApplicationWindow):
    ICON_FALLBACKS = {
        "phone-symbolic": ["smartphone", "phone", "applications-system"],
        "view-refresh-symbolic": ["view-refresh", "reload", "arrow-refresh"],
        "preferences-system-symbolic": ["preferences-system", "settings-configure", "configure"],
        "open-menu-symbolic": ["open-menu", "application-menu", "view-list"],
        "folder-download-symbolic": ["folder-download", "folder", "document-open-folder"],
        "application-x-firmware-symbolic": ["application-x-firmware", "computer", "applications-system"],
        "emblem-downloads-symbolic": ["emblem-downloads", "download", "go-down"],
        "media-playback-start-symbolic": ["media-playback-start", "start-here", "go-next"],
        "emblem-default-symbolic": ["emblem-default", "emblem-ok", "dialog-ok"],
        "emblem-shared-symbolic": ["emblem-shared", "network-workgroup", "folder-publicshare"],
        "document-open-symbolic": ["document-open", "folder-open", "text-x-generic"],
        "media-playback-stop-symbolic": ["media-playback-stop", "process-stop", "dialog-cancel"],
        "user-trash-symbolic": ["user-trash", "edit-delete", "trash-empty"],
        "emblem-system-symbolic": ["emblem-system", "applications-system", "computer"],
        "window-close-symbolic": ["window-close", "dialog-close", "edit-delete"],
        "help-browser-symbolic": ["help-browser", "help-contents", "dialog-question"],
        "utilities-terminal-symbolic": ["utilities-terminal", "terminal", "org.kde.konsole"],
        "web-browser-symbolic": ["web-browser", "internet-web-browser", "applications-internet"],
        "emblem-synchronizing-symbolic": ["emblem-synchronizing", "view-refresh", "reload"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_default_size(900, 700)
        self.set_title(_("Android App Support"))
        self.set_icon_name(self.resolve_icon_name("phone-symbolic"))
        self.system_checker = SystemChecker()
        self.installer = None
        self.manager = None
        self.manager_signals_connected = False
        self.gapps_info_button = None
        self.is_installing = False
        # Set dark theme preference using AdwStyleManager
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        self.setup_ui()
        # Run system check automatically
        GLib.timeout_add(100, self.perform_system_check)

    def resolve_icon_name(self, preferred):
        """Resolve an icon name with desktop-theme friendly fallbacks."""
        theme = Gtk.IconTheme.get_for_display(self.get_display())
        candidates = [preferred] + self.ICON_FALLBACKS.get(preferred, [])
        for name in candidates:
            if theme.has_icon(name):
                return name
        return "applications-system"

    def image_from_icon(self, preferred):
        return Gtk.Image.new_from_icon_name(self.resolve_icon_name(preferred))

    def set_button_icon(self, button, preferred):
        button.set_icon_name(self.resolve_icon_name(preferred))
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
        # Refresh button
        self.refresh_button = Gtk.Button()
        self.set_button_icon(self.refresh_button, "view-refresh-symbolic")
        self.refresh_button.set_tooltip_text(_("Refresh Status"))
        self.refresh_button.connect("clicked", lambda b: self.perform_system_check())
        header.pack_start(self.refresh_button)
        # Menu button
        menu_button = Gtk.MenuButton()
        self.set_button_icon(menu_button, "open-menu-symbolic")
        menu = Gio.Menu()
        menu.append(_("About"), "win.about")
        menu.append(_("Quit"), "app.quit")
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
        # === MANAGEMENT VIEW (Waydroid installed) ===
        self.manage_page = self.create_management_view()
        self.main_stack.add_named(self.manage_page, "manage")
        # === OPERATION VIEW (for init, install APK, etc) ===
        self.operation_page = self.create_operation_view()
        self.main_stack.add_named(self.operation_page, "operation")
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
        spinner = Gtk.Spinner()
        spinner.set_size_request(64, 64)
        spinner.start()
        content.append(spinner)
        title = Gtk.Label()
        title.set_markup(f"<span size='x-large' weight='bold'>{_('Checking Your System')}</span>")
        content.append(title)
        subtitle = Gtk.Label()
        subtitle.set_text(_("Detecting configuration and status..."))
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
        icon = self.image_from_icon("phone-symbolic")
        icon.set_pixel_size(128)
        icon.add_css_class("accent")
        hero_box.append(icon)
        title = Gtk.Label()
        title.set_markup(f"<span size='xx-large' weight='bold'>{_('Android App Support')}</span>")
        title.set_margin_top(12)
        hero_box.append(title)
        desc = Gtk.Label()
        desc.set_text(_("Run Android applications natively on your Parch Linux system"))
        desc.add_css_class("dim-label")
        desc.set_wrap(True)
        desc.set_justify(Gtk.Justification.CENTER)
        hero_box.append(desc)
        main_box.append(hero_box)
        # System status card
        self.status_card = Adw.PreferencesGroup()
        self.status_card.set_title(_("System Status"))
        self.status_card.set_description(_("Current configuration detected on your system"))
        self.repo_row = Adw.ActionRow()
        self.repo_row.set_title(_("Installation Source"))
        repo_icon = self.image_from_icon("folder-download-symbolic")
        self.repo_row.add_prefix(repo_icon)
        self.status_card.add(self.repo_row)
        self.kernel_row = Adw.ActionRow()
        self.kernel_row.set_title(_("Kernel Support"))
        kernel_icon = self.image_from_icon("application-x-firmware-symbolic")
        self.kernel_row.add_prefix(kernel_icon)
        self.status_card.add(self.kernel_row)
        main_box.append(self.status_card)
        # Action card
        action_card = Adw.PreferencesGroup()
        action_card.set_title(_("Get Started"))
        install_row = Adw.ActionRow()
        install_row.set_title(_("Install Waydroid"))
        install_row.set_subtitle(_("Set up Android application support on your system"))
        install_icon = self.image_from_icon("emblem-downloads-symbolic")
        install_row.add_prefix(install_icon)
        self.install_button = Gtk.Button()
        self.install_button.set_label(_("Install"))
        self.install_button.set_valign(Gtk.Align.CENTER)
        self.install_button.add_css_class("suggested-action")
        self.install_button.add_css_class("pill")
        self.install_button.connect("clicked", self.on_install_clicked)
        install_row.add_suffix(self.install_button)
        install_row.set_activatable_widget(self.install_button)
        action_card.add(install_row)
        main_box.append(action_card)
        clamp.set_child(main_box)
        return clamp
    def create_management_view(self):
        """Create comprehensive Waydroid management view with bottom sheet"""
        # Main content in a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        clamp = Adw.Clamp()
        clamp.set_maximum_size(700)
        clamp.set_margin_top(12)
        clamp.set_margin_bottom(12)
        clamp.set_margin_start(12)
        clamp.set_margin_end(12)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        # Status banner
        self.status_banner = Adw.Banner()
        self.status_banner.set_revealed(False)
        main_box.append(self.status_banner)
        # Quick Launch Card
        launch_card = Adw.PreferencesGroup()
        launch_card.set_title(_("Quick Launch"))
        launch_row = Adw.ActionRow()
        launch_row.set_title(_("Launch Waydroid"))
        launch_row.set_subtitle(_("Start the Android environment"))
        launch_icon = self.image_from_icon("media-playback-start-symbolic")
        launch_row.add_prefix(launch_icon)
        self.launch_button = Gtk.Button()
        self.launch_button.set_label(_("Launch"))
        self.launch_button.set_valign(Gtk.Align.CENTER)
        self.launch_button.add_css_class("suggested-action")
        self.launch_button.connect("clicked", self.on_launch_clicked)
        launch_row.add_suffix(self.launch_button)
        launch_row.set_activatable_widget(self.launch_button)
        launch_card.add(launch_row)
        main_box.append(launch_card)
        # System Images Card
        images_card = Adw.PreferencesGroup()
        images_card.set_title(_("System Images"))
        images_card.set_description(_("Download and configure Android images"))
        vanilla_row = Adw.ActionRow()
        vanilla_row.set_title(_("Vanilla Android"))
        vanilla_row.set_subtitle(_("Clean Android without Google services"))
        vanilla_icon = self.image_from_icon("emblem-default-symbolic")
        vanilla_row.add_prefix(vanilla_icon)
        self.vanilla_button = Gtk.Button()
        self.vanilla_button.set_label(_("Download"))
        self.vanilla_button.set_valign(Gtk.Align.CENTER)
        self.vanilla_button.connect("clicked", lambda b: self.on_init_clicked('vanilla'))
        vanilla_row.add_suffix(self.vanilla_button)
        images_card.add(vanilla_row)
        # GApps image
        gapps_row = Adw.ActionRow()
        gapps_row.set_title(_("Google Apps (GApps)"))
        gapps_row.set_subtitle(_("Includes Google Play Store and services"))
        gapps_icon = self.image_from_icon("emblem-shared-symbolic")
        gapps_row.add_prefix(gapps_icon)
        self.gapps_button = Gtk.Button()
        self.gapps_button.set_label(_("Download"))
        self.gapps_button.set_valign(Gtk.Align.CENTER)
        self.gapps_button.connect("clicked", lambda b: self.on_init_clicked('gapps'))
        gapps_row.add_suffix(self.gapps_button)
        images_card.add(gapps_row)
        main_box.append(images_card)
        # App Management Card
        apps_card = Adw.PreferencesGroup()
        apps_card.set_title(_("Application Management"))
        apk_row = Adw.ActionRow()
        apk_row.set_title(_("Install APK"))
        apk_row.set_subtitle(_("Sideload Android applications"))
        apk_icon = self.image_from_icon("document-open-symbolic")
        apk_row.add_prefix(apk_icon)
        apk_button = Gtk.Button()
        apk_button.set_label(_("Choose File"))
        apk_button.set_valign(Gtk.Align.CENTER)
        apk_button.connect("clicked", self.on_install_apk_clicked)
        apk_row.add_suffix(apk_button)
        apk_row.set_activatable_widget(apk_button)
        apps_card.add(apk_row)
        main_box.append(apps_card)
        # Session Control Card
        session_card = Adw.PreferencesGroup()
        session_card.set_title(_("Session Control"))
        start_row = Adw.ActionRow()
        start_row.set_title(_("Start Session"))
        start_row.set_subtitle(_("Start Waydroid container and session"))
        start_icon = self.image_from_icon("media-playback-start-symbolic")
        start_row.add_prefix(start_icon)
        self.start_button = Gtk.Button()
        self.start_button.set_label(_("Start"))
        self.start_button.set_valign(Gtk.Align.CENTER)
        self.start_button.connect("clicked", self.on_start_session_clicked)
        start_row.add_suffix(self.start_button)
        session_card.add(start_row)
        # Stop session
        stop_row = Adw.ActionRow()
        stop_row.set_title(_("Stop Session"))
        stop_row.set_subtitle(_("Stop Waydroid session and container"))
        stop_icon = self.image_from_icon("media-playback-stop-symbolic")
        stop_row.add_prefix(stop_icon)
        self.stop_button = Gtk.Button()
        self.stop_button.set_label(_("Stop"))
        self.stop_button.set_valign(Gtk.Align.CENTER)
        self.stop_button.add_css_class("destructive-action")
        self.stop_button.connect("clicked", self.on_stop_session_clicked)
        stop_row.add_suffix(self.stop_button)
        session_card.add(stop_row)
        # Restart session
        restart_row = Adw.ActionRow()
        restart_row.set_title(_("Restart Session"))
        restart_row.set_subtitle(_("Restart Waydroid session"))
        restart_icon = self.image_from_icon("view-refresh-symbolic")
        restart_row.add_prefix(restart_icon)
        self.restart_button = Gtk.Button()
        self.restart_button.set_label(_("Restart"))
        self.restart_button.set_valign(Gtk.Align.CENTER)
        self.restart_button.connect("clicked", self.on_restart_session_clicked)
        restart_row.add_suffix(self.restart_button)
        session_card.add(restart_row)
        main_box.append(session_card)
        # Reset row (moved outside advanced)
        reset_card = Adw.PreferencesGroup()
        reset_card.set_title(_("Reset"))
        reset_row = Adw.ActionRow()
        reset_row.set_title(_("Reset Waydroid"))
        reset_row.set_subtitle(_("Delete and reinitialize Waydroid"))
        reset_icon = self.image_from_icon("user-trash-symbolic")
        reset_row.add_prefix(reset_icon)
        self.reset_button = Gtk.Button()
        self.reset_button.set_label(_("Reset"))
        self.reset_button.add_css_class("destructive-action")
        self.reset_button.set_valign(Gtk.Align.CENTER)
        self.reset_button.connect("clicked", self.on_reset_clicked)
        reset_row.add_suffix(self.reset_button)
        reset_card.add(reset_row)
        main_box.append(reset_card)
        # Status Information - Expandable row
        self.info_card = Adw.PreferencesGroup()
        self.info_card.set_title(_("Status Information"))
        status_expander = Adw.ExpanderRow()
        status_expander.set_title(_("View Detailed Status"))
        status_expander.set_subtitle(_("Session, container, and system info"))
        status_icon = self.image_from_icon("emblem-system-symbolic")
        status_expander.add_prefix(status_icon)
        self.session_status_row = Adw.ActionRow()
        self.session_status_row.set_title(_("Session Status"))
        status_expander.add_row(self.session_status_row)
        self.container_status_row = Adw.ActionRow()
        self.container_status_row.set_title(_("Container Status"))
        status_expander.add_row(self.container_status_row)
        self.image_status_row = Adw.ActionRow()
        self.image_status_row.set_title(_("Android Version"))
        status_expander.add_row(self.image_status_row)
        self.gapps_status_row = Adw.ActionRow()
        self.gapps_status_row.set_title(_("Google Apps"))
        status_expander.add_row(self.gapps_status_row)
        self.ip_status_row = Adw.ActionRow()
        self.ip_status_row.set_title(_("IP Address"))
        status_expander.add_row(self.ip_status_row)
        self.info_card.add(status_expander)
        main_box.append(self.info_card)
        clamp.set_child(main_box)
        scrolled.set_child(clamp)
        return scrolled
    def create_operation_view(self):
        """Create view for operations (init, install APK, etc)"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
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
        status_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.status_spinner = Gtk.Spinner()
        self.status_spinner.set_size_request(24, 24)
        self.status_spinner.start()
        status_header.append(self.status_spinner)
        self.operation_status = Gtk.Label()
        self.operation_status.set_markup(f"<span size='large' weight='bold'>{_('Preparing...')}</span>")
        self.operation_status.set_xalign(0)
        self.operation_status.set_hexpand(True)
        status_header.append(self.operation_status)
        status_box.append(status_header)
        self.operation_progress = Gtk.ProgressBar()
        self.operation_progress.set_show_text(False)
        self.operation_progress.pulse()
        self.operation_progress.add_css_class("osd")
        status_box.append(self.operation_progress)
        content.append(status_box)
        # Terminal section
        terminal_frame = Gtk.Frame()
        terminal_frame.set_vexpand(True)
        terminal_frame.add_css_class("view")
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        if HAS_VTE:
            self.operation_terminal = Vte.Terminal()
            self.operation_terminal.set_font(Pango.FontDescription("Monospace 11"))
            self.operation_terminal.set_scroll_on_output(True)
            self.operation_terminal.set_scrollback_lines(10000)
            scrolled.set_child(self.operation_terminal)
        else:
            self.operation_terminal_view = Gtk.TextView()
            self.operation_terminal_view.set_editable(False)
            self.operation_terminal_view.set_monospace(True)
            self.operation_terminal_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            self.operation_terminal_view.set_left_margin(12)
            self.operation_terminal_view.set_right_margin(12)
            self.operation_terminal_view.set_top_margin(12)
            self.operation_terminal_view.set_bottom_margin(12)
            self.operation_terminal_buffer = self.operation_terminal_view.get_buffer()
            scrolled.set_child(self.operation_terminal_view)
            self.operation_terminal = None
        terminal_frame.set_child(scrolled)
        content.append(terminal_frame)
        # Button bar
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)
        self.operation_done_button = Gtk.Button(label=_("Done"))
        self.operation_done_button.set_visible(False)
        self.operation_done_button.add_css_class("suggested-action")
        self.operation_done_button.connect("clicked", self.on_operation_done_clicked)
        button_box.append(self.operation_done_button)
        self.operation_cancel_button = Gtk.Button(label=_("Cancel"))
        self.operation_cancel_button.connect("clicked", self.on_operation_cancel)
        button_box.append(self.operation_cancel_button)
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
        if result['waydroid_installed']:
            # Create manager if not exists
            if not self.manager:
                self.manager = WaydroidManager()
            # Get detailed status
            status = self.manager.get_status()
            self.update_management_view(status)
            self.main_stack.set_visible_child_name("manage")
        else:
            self.update_welcome_view(result)
            self.main_stack.set_visible_child_name("welcome")
        return False
    def update_welcome_view(self, result):
        """Update welcome view"""
        if result['system_compatible']:
            self.repo_row.set_subtitle("Arch Linux Extra Repository (fast installation)")
            self.install_button.set_sensitive(True)
        else:
            self.repo_row.set_subtitle("Not available")
            self.install_button.set_sensitive(False)
        if result['kernel_modules_ok']:
            self.kernel_row.set_subtitle("All modules available")
        else:
            self.kernel_row.set_subtitle("Some modules missing")
    def update_management_view(self, status):
        """Update management view with current status"""
        # Update session status
        if status['session_running']:
            self.session_status_row.set_subtitle(_("Running"))
            self.start_button.set_sensitive(False)
            self.stop_button.set_sensitive(True)
            self.launch_button.set_sensitive(True)
            self.restart_button.set_sensitive(True)
        else:
            self.session_status_row.set_subtitle(_("Stopped"))
            self.start_button.set_sensitive(True)
            self.stop_button.set_sensitive(False)
            self.launch_button.set_sensitive(False)
            self.restart_button.set_sensitive(False)
        # Update container status
        if status['container_running']:
            self.container_status_row.set_subtitle(_("Active"))
        else:
            self.container_status_row.set_subtitle(_("Inactive"))
        # Update image info
        if status['initialized']:
            self.image_status_row.set_subtitle(f"Android {status['android_version']}")
            self.status_banner.set_revealed(False)
        else:
            self.image_status_row.set_subtitle("Not initialized")
            self.status_banner.set_title("System images not downloaded")
            self.status_banner.set_button_label("Download Images")
            self.status_banner.set_revealed(True)
            self.launch_button.set_sensitive(False)
        # Update GApps status
        if status['has_gapps']:
            self.gapps_status_row.set_subtitle("Installed (requires registration)")
            # Add button to show GApps registration info
            if self.gapps_info_button is None:
                self.gapps_info_button = Gtk.Button()
                self.set_button_icon(self.gapps_info_button, "help-browser-symbolic")
                self.gapps_info_button.set_valign(Gtk.Align.CENTER)
                self.gapps_info_button.add_css_class("flat")
                self.gapps_info_button.set_tooltip_text("Show registration info")
                self.gapps_info_button.connect("clicked", self.show_gapps_registration_info)
                self.gapps_status_row.add_suffix(self.gapps_info_button)
        else:
            self.gapps_status_row.set_subtitle("Not installed")
        # Update IP
        self.ip_status_row.set_subtitle(status['ip_address'])
        # Update image buttons
        self.vanilla_button.set_label("Download")
        self.gapps_button.set_label("Download")
        self.vanilla_button.set_sensitive(True)
        self.gapps_button.set_sensitive(True)
        if status['initialized']:
            current_type = 'gapps' if status['has_gapps'] else 'vanilla'
            if current_type == 'vanilla':
                self.vanilla_button.set_label("Installed")
                self.vanilla_button.set_sensitive(False)
                self.gapps_button.set_label("Switch to GApps")
                self.gapps_button.set_sensitive(True)
            else:
                self.gapps_button.set_label("Installed")
                self.gapps_button.set_sensitive(False)
                self.vanilla_button.set_label("Switch to Vanilla")
                self.vanilla_button.set_sensitive(True)
    def on_install_clicked(self, button):
        """Handle install button click"""
        result = self.system_checker.get_last_result()
        if not result['system_compatible']:
            self.show_toast("No installation source available")
            return
        source = 'extra'
        source_name = "Arch Linux Extra Repository"
        dialog = Adw.MessageDialog(transient_for=self)
        dialog.set_heading(_("Install Waydroid?"))
        dialog.set_body(f"Waydroid will be installed from {source_name}.\n\nThis process may take a few minutes.")
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("install", _("Install"))
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("install")
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda d, r: self.start_installation(source) if r == "install" else None)
        dialog.present()
    def on_init_clicked(self, image_type):
        """Handle initialization button click"""
        # Check if already initialized
        if self.manager:
            status = self.manager.get_status()
            if status['initialized']:
                dialog = Adw.MessageDialog(transient_for=self)
                dialog.set_heading(_("Reinitialize Waydroid?"))
                dialog.set_body(f"This will download new {image_type} images and replace existing data.\n\nAll Android data will be lost!")
                dialog.add_response("cancel", _("Cancel"))
                dialog.add_response("reinit", "Reinitialize")
                dialog.set_response_appearance("reinit", Adw.ResponseAppearance.DESTRUCTIVE)
                dialog.set_default_response("cancel")
                dialog.set_close_response("cancel")
                dialog.connect("response", lambda d, r: self.start_initialization(image_type, True) if r == "reinit" else None)
                dialog.present()
                return
        # Show GApps warning if needed
        if image_type == 'gapps':
            dialog = Adw.MessageDialog(transient_for=self)
            dialog.set_heading(_("Download Google Apps?"))
            dialog.set_body(_("Google Play requires device registration after installation.") + "\n\n" + _("You'll need to register your device manually to use the Play Store."))
            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("learn", _("Learn More"))
            dialog.add_response("proceed", _("Proceed"))
            dialog.set_response_appearance("proceed", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("proceed")
            dialog.set_close_response("cancel")
            def on_gapps_response(d, r):
                if r == "proceed":
                    self.start_initialization(image_type, False)
                elif r == "learn":
                    self.show_gapps_registration_info()
            dialog.connect("response", on_gapps_response)
            dialog.present()
        else:
            self.start_initialization(image_type, False)
    def on_reset_clicked(self, button):
        """Handle reset button click"""
        dialog = Adw.MessageDialog(transient_for=self)
        dialog.set_heading(_("Reset Waydroid?"))
        dialog.set_body(_("This will delete all Android data and reinitialize with new images."))
        type_row = Adw.ComboRow()
        type_row.set_title(_("Image Type"))
        model = Gio.ListStore.new(Gtk.StringObject)
        model.append(Gtk.StringObject.new("vanilla"))
        model.append(Gtk.StringObject.new("gapps"))
        type_row.set_model(model)
        type_row.set_selected(0)
        dialog.set_extra_child(type_row)
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("reset", _("Reset"))
        dialog.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda d, r: self.start_initialization(type_row.get_selected_item().get_string(), True) if r == "reset" else None)
        dialog.present()
    def start_installation(self, source):
        """Start Waydroid installation"""
        self.main_stack.set_visible_child_name("operation")
        self.clear_operation_terminal()
        self.installer = WaydroidInstaller()
        self.installer.connect('output', self.on_operation_output)
        self.installer.connect('status', self.on_operation_status)
        self.installer.connect('progress', self.on_operation_progress)
        self.installer.connect('completed', self.on_installation_completed)
        self.installer.connect('password-required', self.on_password_required)
        thread = threading.Thread(target=self.installer.install, args=(source,), daemon=True)
        thread.start()

    def ensure_manager(self):
        """Create manager and connect signals once."""
        if not self.manager:
            self.manager = WaydroidManager()
        if not self.manager_signals_connected:
            self.manager.connect('output', self.on_operation_output)
            self.manager.connect('status', self.on_operation_status)
            self.manager.connect('progress', self.on_operation_progress)
            self.manager.connect('completed', self.on_operation_completed)
            self.manager.connect('password-required', self.on_password_required)
            self.manager_signals_connected = True
    def start_initialization(self, image_type, force):
        """Start Waydroid initialization"""
        self.main_stack.set_visible_child_name("operation")
        self.clear_operation_terminal()
        self.ensure_manager()
        thread = threading.Thread(target=self.manager.initialize, args=(image_type, force), daemon=True)
        thread.start()
    def on_start_session_clicked(self, button):
        """Start Waydroid session"""
        self.main_stack.set_visible_child_name("operation")
        self.clear_operation_terminal()
        self.ensure_manager()
        thread = threading.Thread(target=self.manager.start_session, daemon=True)
        thread.start()
    def on_stop_session_clicked(self, button):
        """Stop Waydroid session"""
        if self.manager:
            if self.manager.stop_session():
                self.show_toast("Waydroid stopped successfully")
                self.perform_system_check()
    def on_restart_session_clicked(self, button):
        """Restart Waydroid session"""
        dialog = Adw.MessageDialog(transient_for=self)
        dialog.set_heading("Restart Session?")
        dialog.set_body("This will stop and start the Waydroid session.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("restart", "Restart")
        dialog.set_response_appearance("restart", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda d, r: self.start_restart_session() if r == "restart" else None)
        dialog.present()
    def start_restart_session(self):
        self.main_stack.set_visible_child_name("operation")
        self.clear_operation_terminal()
        self.ensure_manager()
        thread = threading.Thread(target=self.manager.restart_session, daemon=True)
        thread.start()
    def on_launch_clicked(self, button):
        """Launch Waydroid UI"""
        if self.manager and self.manager.launch_ui():
            self.show_toast("Waydroid launched")
        else:
            self.show_toast("Failed to launch Waydroid")
    def on_install_apk_clicked(self, button):
        """Show file chooser for APK installation"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select APK File")
        # APK filter
        apk_filter = Gtk.FileFilter()
        apk_filter.set_name("Android APK files")
        apk_filter.add_pattern("*.apk")
        all_filter = Gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(apk_filter)
        filter_list.append(all_filter)
        dialog.set_filters(filter_list)
        dialog.set_default_filter(apk_filter)
        dialog.open(self, None, self.on_apk_file_selected)
    def on_apk_file_selected(self, dialog, result):
        """Handle APK file selection"""
        try:
            file = dialog.open_finish(result)
            if file:
                apk_path = file.get_path()
                self.install_apk(apk_path)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                self.show_toast(f"Error selecting file: {e}")
    def install_apk(self, apk_path):
        """Install selected APK"""
        self.main_stack.set_visible_child_name("operation")
        self.clear_operation_terminal()
        self.ensure_manager()
        thread = threading.Thread(target=self.manager.install_apk, args=(apk_path,), daemon=True)
        thread.start()

    def show_gapps_registration_info(self, button=None):
        """Show GApps registration information in a bottom sheet"""
        # Create bottom sheet dialog
        dialog = Adw.Dialog()
        dialog.set_title("Google Play Certification")
        dialog.set_content_width(500)
        dialog.set_content_height(600)
        dialog.set_presentation_mode(Adw.DialogPresentationMode.BOTTOM_SHEET)
        # Toolbar view for the dialog
        toolbar_view = Adw.ToolbarView()
        # Header bar
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        # Close button
        close_button = Gtk.Button()
        self.set_button_icon(close_button, "window-close-symbolic")
        close_button.connect("clicked", lambda b: dialog.close())
        header.pack_start(close_button)
        # Open docs button
        docs_button = Gtk.Button()
        docs_button.set_label("Open Docs")
        docs_button.add_css_class("suggested-action")
        docs_button.connect("clicked", lambda b: self.open_gapps_docs())
        header.pack_end(docs_button)
        toolbar_view.add_top_bar(header)
        # Content area with clamp
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        clamp = Adw.Clamp()
        clamp.set_maximum_size(500)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        # Introduction
        intro_label = Gtk.Label()
        intro_label.set_markup("<b>Register Your Device</b>")
        intro_label.set_xalign(0)
        content_box.append(intro_label)
        desc_label = Gtk.Label()
        desc_label.set_text("To use Google Play Store with Waydroid, you need to register your device with Google.")
        desc_label.set_wrap(True)
        desc_label.set_xalign(0)
        desc_label.add_css_class("dim-label")
        content_box.append(desc_label)
        # Steps group
        steps_group = Adw.PreferencesGroup()
        steps_group.set_title("Registration Steps")
        # Step 1
        step1 = Adw.ActionRow()
        step1.set_title("1. Start Waydroid")
        step1.set_subtitle("Launch Waydroid from the main screen")
        step1_icon = self.image_from_icon("media-playback-start-symbolic")
        step1.add_prefix(step1_icon)
        steps_group.add(step1)
        # Step 2
        step2 = Adw.ExpanderRow()
        step2.set_title("2. Get Android ID")
        step2.set_subtitle("Open terminal and run commands")
        step2_icon = self.image_from_icon("utilities-terminal-symbolic")
        step2.add_prefix(step2_icon)
        step2_shell = Adw.ActionRow()
        step2_shell.set_title("Open Waydroid shell")
        step2_shell.set_subtitle("sudo waydroid shell")
        step2.add_row(step2_shell)
        step2_id = Adw.ActionRow()
        step2_id.set_title("Run Android ID query")
        step2_id.set_subtitle('ANDROID_RUNTIME_ROOT=/apex/com.android.runtime ANDROID_DATA=/data ANDROID_TZDATA_ROOT=/apex/com.android.tzdata ANDROID_I18N_ROOT=/apex/com.android.i18n sqlite3 /data/data/com.google.android.gsf/databases/gservices.db "select * from main where name = \\"android_id\\";"')
        step2_id.set_subtitle_lines(3)
        step2.add_row(step2_id)
        steps_group.add(step2)
        # Step 3
        step3 = Adw.ActionRow()
        step3.set_title("3. Register Device")
        step3.set_subtitle("Copy the ID and register at Google")
        step3_icon = self.image_from_icon("web-browser-symbolic")
        step3.add_prefix(step3_icon)
        register_button = Gtk.Button()
        register_button.set_label("Open Registration")
        register_button.set_valign(Gtk.Align.CENTER)
        register_button.connect("clicked", lambda b: self.open_google_registration())
        step3.add_suffix(register_button)
        steps_group.add(step3)
        # Step 4
        step4 = Adw.ActionRow()
        step4.set_title("4. Wait and Restart")
        step4.set_subtitle("Wait 10-20 minutes, then restart Waydroid")
        step4_icon = self.image_from_icon("emblem-synchronizing-symbolic")
        step4.add_prefix(step4_icon)
        steps_group.add(step4)
        content_box.append(steps_group)
        # Help box
        help_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        help_box.set_margin_top(12)
        help_label = Gtk.Label()
        help_label.set_markup("<b>Need Help?</b>")
        help_label.set_xalign(0)
        help_box.append(help_label)
        help_desc = Gtk.Label()
        help_desc.set_text("Visit the official Waydroid documentation for detailed instructions and troubleshooting.")
        help_desc.set_wrap(True)
        help_desc.set_xalign(0)
        help_desc.add_css_class("dim-label")
        help_box.append(help_desc)
        content_box.append(help_box)
        clamp.set_child(content_box)
        scrolled.set_child(clamp)
        toolbar_view.set_content(scrolled)
        dialog.set_child(toolbar_view)
        dialog.present(self)
    def open_gapps_docs(self):
        """Open GApps documentation"""
        import webbrowser
        webbrowser.open("https://docs.waydro.id/faq/google-play-certification")
        self.show_toast("Opening documentation in browser")
    def open_google_registration(self):
        """Open Google device registration page"""
        import webbrowser
        webbrowser.open("https://www.google.com/android/uncertified/")
        self.show_toast("Opening Google registration page")
    def clear_operation_terminal(self):
        """Clear operation terminal"""
        if HAS_VTE and self.operation_terminal:
            self.operation_terminal.reset(True, True)
        else:
            self.operation_terminal_buffer.set_text("")
        self.operation_done_button.set_visible(False)
        self.operation_cancel_button.set_visible(True)
        self.status_spinner.start()
    def on_operation_output(self, source, text):
        """Handle operation output"""
        def update():
            if HAS_VTE and self.operation_terminal:
                self.operation_terminal.feed(text.encode('utf-8'))
            else:
                end_iter = self.operation_terminal_buffer.get_end_iter()
                self.operation_terminal_buffer.insert(end_iter, text)
                mark = self.operation_terminal_buffer.get_insert()
                self.operation_terminal_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
        GLib.idle_add(update)
    def on_operation_status(self, source, status):
        """Handle operation status update"""
        GLib.idle_add(lambda: self.operation_status.set_markup(f"<span size='large' weight='bold'>{status}</span>"))
    def on_operation_progress(self, source, fraction):
        """Handle operation progress"""
        def update():
            if fraction < 0:
                self.operation_progress.pulse()
            else:
                self.operation_progress.set_fraction(fraction)
                self.operation_progress.set_show_text(True)
        GLib.idle_add(update)
    def on_operation_completed(self, source, success):
        """Handle operation completion"""
        def finalize():
            self.operation_cancel_button.set_visible(False)
            self.operation_done_button.set_visible(True)
            self.status_spinner.stop()
            if success:
                self.operation_status.set_markup(f"<span size='large' weight='bold'>✓ {_('Operation Complete!')}</span>")
                self.operation_progress.set_fraction(1.0)
            else:
                self.operation_status.set_markup(f"<span size='large' weight='bold'>✗ {_('Operation Failed')}</span>")
        GLib.idle_add(finalize)
    def on_installation_completed(self, installer, success):
        """Handle installation completion"""
        def finalize():
            self.operation_cancel_button.set_visible(False)
            self.operation_done_button.set_visible(True)
            self.status_spinner.stop()
            if success:
                self.operation_status.set_markup(f"<span size='large' weight='bold'>✓ {_('Installation Complete!')}</span>")
                self.operation_progress.set_fraction(1.0)
                self.show_toast(_("Waydroid installed successfully"))
            else:
                self.operation_status.set_markup(f"<span size='large' weight='bold'>✗ {_('Installation Failed')}</span>")
                self.show_toast(_("Installation failed"))
        GLib.idle_add(finalize)
    def on_password_required(self, source):
        """Handle password request"""
        def ask():
            dialog = Adw.MessageDialog(transient_for=self)
            dialog.set_heading(_("Authentication Required"))
            dialog.set_body(_("Administrator privileges are required to continue."))
            entry = Adw.PasswordEntryRow()
            entry.set_title(_("Password"))
            dialog.set_extra_child(entry)
            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("auth", _("Authenticate"))
            dialog.set_response_appearance("auth", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("auth")
            def on_response(d, r):
                if r == "auth":
                    password = entry.get_text()
                    if self.installer:
                        self.installer.provide_password(password)
                    if self.manager:
                        self.manager.provide_password(password)
                else:
                    if self.installer:
                        self.installer.cancel()
                    if self.manager:
                        self.manager.cancel()
            dialog.connect("response", on_response)
            entry.connect("activate", lambda e: dialog.response("auth"))
            dialog.present()
        GLib.idle_add(ask)
    def on_operation_cancel(self, button):
        """Cancel current operation"""
        if self.installer:
            self.installer.cancel()
        if self.manager:
            self.manager.cancel()
    def on_operation_done_clicked(self, button):
        """Return to management view after operation"""
        self.main_stack.set_visible_child_name("checking")
        GLib.timeout_add(500, self.perform_system_check)
    def show_toast(self, message):
        """Show toast notification"""
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)
    def setup_actions(self):
        """Setup window actions"""
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)
    def on_about(self, action, param):
        """Show about dialog"""
        about = Adw.AboutWindow(transient_for=self)
        about.set_application_name(_("Android App Support"))
        about.set_application_icon("com.parchlinux.parchdroid")
        about.set_developer_name(_("Parch Linux"))
        about.set_version("1.0.0")
        about.set_comments(_("Complete Waydroid management for Parch Linux"))
        about.set_website("https://parchlinux.com")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.add_credit_section(_("Contributors"), ["Parch Linux Team"])
        about.add_link("Waydroid Documentation", "https://docs.waydro.id/")
        about.present()
