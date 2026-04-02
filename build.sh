#!/usr/bin/env bash
set -e

VERSION=1.0.0
NAME=podfather
TARBALL="${NAME}-${VERSION}.tar.gz"
RPMBUILD_DIR="$HOME/rpmbuild"

echo "==> Setting up rpmbuild directory structure..."
mkdir -p "$RPMBUILD_DIR"/{SOURCES,SPECS,BUILD,RPMS,SRPMS,BUILDROOT}

echo "==> Creating source tarball..."
tar czf "$RPMBUILD_DIR/SOURCES/$TARBALL" \
    --transform "s|^\.|${NAME}-${VERSION}|" \
    --exclude "./.git" \
    --exclude "./build" \
    --exclude "./dist" \
    --exclude "./__pycache__" \
    --exclude "./src/__pycache__" \
    .

echo "==> Copying RPM spec..."
cp podfather.rpm.spec "$RPMBUILD_DIR/SPECS/${NAME}.spec"

echo "==> Building RPM..."
rpmbuild -bb "$RPMBUILD_DIR/SPECS/${NAME}.spec"

echo ""
echo "RPM built:"
find "$RPMBUILD_DIR/RPMS" -name "${NAME}-*.rpm"
echo ""
echo "Install with:"
find "$RPMBUILD_DIR/RPMS" -name "${NAME}-*.rpm" -exec echo "  sudo rpm -i {}" \;
