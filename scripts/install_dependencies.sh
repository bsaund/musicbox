#!/usr/bin/env bash
# install_dependencies.sh
#
# Install all system (apt) and Python (pip) dependencies for musicbox.
# Safe to run multiple times — skips packages that are already present.
#
# Assumes Python packages are installed into the active virtual environment
# (i.e. run this from an activated venv — do NOT run with sudo).
# apt packages that are missing will be installed via sudo apt-get.
#
# Usage (activate your venv first):
#   source /path/to/venv/bin/activate
#   bash scripts/install_dependencies.sh

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
        log "Installing apt packages (requires sudo): ${MISSING_APT[*]}"
        sudo apt-get update -qq
        sudo apt-get install -y "${MISSING_APT[@]}"
    else
        log "All apt packages already installed."
    fi
fi

# ── Python packages ──────────────────────────────────────────────────────────

if ! command -v python3 &>/dev/null; then
    warn "python3 not found. Cannot install Python dependencies."
    exit 1
fi

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    log "Active venv: $VIRTUAL_ENV"
else
    warn "No active virtual environment detected (VIRTUAL_ENV is unset)."
    warn "Python packages will be installed into whichever 'python3' is on PATH."
    warn "Consider activating a venv first: source /path/to/venv/bin/activate"
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
log ""
log "Raspberry Pi services (barcode scanner / bluetooth remote) also need:"
log "  pip install -r $SCRIPT_DIR/requirements-pi.txt"
