# Parchdroid

Parchdroid is a Waydroid management application for Parch Linux. It provides a graphical interface for installing, configuring, and managing Android application support on your system through a GTK4 and Adwaita interface.

## Features

Parchdroid checks your system for Waydroid compatibility, installs Waydroid from system repositories, initializes Android system images with vanilla or Google Apps variants, manages Waydroid sessions including start, stop and restart, installs APK files through a file chooser dialog, and displays real-time system status information. The interface supports Persian and English languages.

## Requirements

Parchdroid requires a Parch Linux or Arch Linux system with a Wayland session. The system must support the binder and ashmem kernel modules for Waydroid functionality.

## Building and Installation

Build and install the package from the PKGBUILD with makepkg:

```
makepkg -si
```

## Runtime Dependencies

Parchdroid depends on python, python-gobject, gtk4, libadwaita, and python-pexpect. Optional support for in-app terminal output requires vte.

## License

GNU Affero General Public License v3.0 or later. See LICENSE for details.
