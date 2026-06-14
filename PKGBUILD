# Maintainer: Parch Linux Team
# Contributor: Parch Linux Team

pkgname=parchdroid
_pkgname=parchdroid
pkgver=1.0.0
pkgrel=1
pkgdesc="Android App Support for Parch Linux, Waydroid Manager"
arch=('any')
url="https://github.com/parchlinux/parchdroid"
license=('AGPL-3.0-or-later')
depends=(
    'python'
    'python-gobject'
    'gtk4'
    'libadwaita'
    'python-pexpect'
    'vte4'
)
makedepends=('gettext')
options=('!emptydirs')
source=("${pkgname}-${pkgver}.tar.gz::https://github.com/parchlinux/parchdroid/archive/${pkgver}.tar.gz")
sha256sums=('SKIP')

build() {
    cd "${srcdir}/${_pkgname}-${pkgver}"
    msgfmt locale/fa/LC_MESSAGES/parchdroid.po -o locale/fa/LC_MESSAGES/parchdroid.mo
}

package() {
    cd "${srcdir}/${_pkgname}-${pkgver}"

    _pythonlib="/usr/lib/python$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')/site-packages"

    install -dm755 "${pkgdir}${_pythonlib}"
    cp -r src/core "${pkgdir}${_pythonlib}/"
    cp -r src/ui "${pkgdir}${_pythonlib}/"
    install -m644 src/main.py "${pkgdir}${_pythonlib}/"

    install -dm755 "${pkgdir}/usr/bin"
    cat > "${pkgdir}/usr/bin/parchdroid" << LAUNCHER
#!/bin/sh
exec /usr/bin/python3 "${_pythonlib}/main.py"
LAUNCHER
    chmod 755 "${pkgdir}/usr/bin/parchdroid"

    install -dm755 "${pkgdir}/usr/share/applications"
    install -m644 parchdroid.desktop "${pkgdir}/usr/share/applications/"

    install -dm755 "${pkgdir}/usr/share/locale/fa/LC_MESSAGES"
    install -m644 locale/fa/LC_MESSAGES/parchdroid.mo "${pkgdir}/usr/share/locale/fa/LC_MESSAGES/"

    install -dm755 "${pkgdir}/usr/share/icons/hicolor/scalable/apps"
    install -m644 icons/hicolor/scalable/apps/com.parchlinux.parchdroid.svg \
        "${pkgdir}/usr/share/icons/hicolor/scalable/apps/"

    install -dm755 "${pkgdir}/usr/share/licenses/${pkgname}"
    install -m644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/"
}
