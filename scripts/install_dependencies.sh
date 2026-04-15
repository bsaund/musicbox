#!/usr/bin/env bash
# install_dependencies.sh
#
# Install all system (apt) and Python (pip) dependencies for musicbox.
# Safe to run multiple times — skips packages that are already present.
#
# Usage:
#   cd /path/to/musicbox
#   sudo bash scripts/install_dependencies.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

# ── Helpers ────────────────────────────────────────────────────────────────

log()  { echo "[install] $*"; }
warn() { echo "[install] WARNING: $*" >&2; }

apt_installed() { dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "install ok installed"; }
pip_installed() { python3 -c "import importlib.util; exit(0 if importlib.util.find_spec('$1') else 1)" 2>/dev/null; }

# ── Check we can use apt ────────────────────────────────────────────────────

if ! command -v apt-get &>/dev/null; then
    warn "apt-get not found. Skipping system package installation."
    warn "Install these manually: cdparanoia lame eject libdiscid0"
    APT_AVAILABLE=false
else
    APT_AVAILABLE=true
fi

# ── System packages ─────────────────────────────────────────────────────────

APT_PACKAGES=(
    # CD ripper (rip_cd.py)
    cdparanoia    # audio CD ripping with error correction
    lame          # MP3 encoder
    eject         # eject the CD tray when done
    libdiscid0    # C library used by python discid package

    # Python3 (may already be present on Pi / desktop)
    python3
    python3-pip
)

if [[ "$APT_AVAILABLE" == true ]]; then
    MISSING_APT=()
    for pkg in "${APT_PACKAGES[@]}"; do
        if ! apt_installed "$pkg"; then
            MISSING_APT+=("$pkg")
        fi
    done

    if [[ ${#MISSING_APT[@]} -gt 0 ]]; then
        log "Installing apt packages: ${MISSING_APT[*]}"
        apt-get update -qq
        apt-get install -y "${MISSING_APT[@]}"
    else
        log "All apt packages already installed."
    fi
fi

# ── Python packages ──────────────────────────────────────────────────────────

if ! command -v python3 &>/dev/null; then
    warn "python3 not found. Cannot install Python dependencies."
    exit 1
fi

if ! command -v pip3 &>/dev/null; then
    warn "pip3 not found. Trying 'python3 -m pip' instead."
    PIP="python3 -m pip"
else
    PIP="pip3"
fi

log "Installing Python dependencies from $REQUIREMENTS ..."
$PIP install --quiet -r "$REQUIREMENTS"

log ""
log "All dependencies installed successfully."
log "To run the CD ripper:    python3 $REPO_ROOT/code/rip_cd.py"
log "To generate the binder: python3 $REPO_ROOT/code/barcode_map.py"
