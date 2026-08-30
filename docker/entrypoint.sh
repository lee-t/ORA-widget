#!/usr/bin/env bash
set -Eeuo pipefail

ENGINE_ROOT=/app/engine
ENGINE_DIR="$ENGINE_ROOT/openra-cnc"
ENGINE_MARKER="$ENGINE_ROOT/.openra-cnc.marker"
CONFIG_ROOT="${HOME}/.config/openra"
CONTENT_DIR="$CONFIG_ROOT/Content/cnc"
CONTENT_MARKER="$CONFIG_ROOT/.cnc-content.marker"

ENGINE_URL="https://github.com/OpenRA/OpenRA/releases/download/${OPENRA_RELEASE}/OpenRA-Tiberian-Dawn-x86_64.AppImage"
ENGINE_FINGERPRINT="release=${OPENRA_RELEASE} sha256=${OPENRA_APPIMAGE_SHA256}"
CONTENT_FINGERPRINT="url=${CNC_CONTENT_URL} sha256=${CNC_CONTENT_SHA256}"

fail() {
    printf 'entrypoint: %s\n' "$*" >&2
    exit 1
}

verify_sha256() {
    local expected=$1
    local file=$2
    printf '%s  %s\n' "$expected" "$file" | sha256sum --check --status \
        || fail "SHA-256 verification failed for ${file}"
}

engine_ready() {
    [[ -f "$ENGINE_MARKER" ]] \
        && [[ "$(<"$ENGINE_MARKER")" == "$ENGINE_FINGERPRINT" ]] \
        && [[ -x "$ENGINE_DIR/usr/bin/openra-cnc" ]] \
        && [[ -x "$ENGINE_DIR/usr/bin/openra-cnc-utility" ]] \
        && [[ -f "$ENGINE_DIR/usr/lib/openra/mods/cnc/mod.yaml" ]]
}

content_ready() {
    [[ -f "$CONTENT_MARKER" ]] \
        && [[ "$(<"$CONTENT_MARKER")" == "$CONTENT_FINGERPRINT" ]] \
        && [[ -s "$CONTENT_DIR/conquer.mix" ]]
}

setup_engine() (
    set -Eeuo pipefail
    mkdir -p "$ENGINE_ROOT"
    local tmp old appimage
    tmp=$(mktemp -d "$ENGINE_ROOT/.openra-cnc.tmp.XXXXXX")
    trap 'rm -rf -- "$tmp"' EXIT
    appimage="$tmp/OpenRA-Tiberian-Dawn-x86_64.AppImage"

    printf 'entrypoint: downloading OpenRA %s\n' "$OPENRA_RELEASE"
    curl --fail --location --retry 3 --retry-all-errors --silent --show-error \
        "$ENGINE_URL" --output "$appimage"
    verify_sha256 "$OPENRA_APPIMAGE_SHA256" "$appimage"
    chmod 0755 "$appimage"

    (cd "$tmp" && "$appimage" --appimage-extract >/dev/null)
    [[ -x "$tmp/squashfs-root/usr/bin/openra-cnc-utility" ]] \
        || fail "OpenRA archive did not contain the CNC utility"

    old="$ENGINE_ROOT/.openra-cnc.previous.$$"
    if [[ -e "$ENGINE_DIR" || -L "$ENGINE_DIR" ]]; then
        mv "$ENGINE_DIR" "$old"
    fi
    mv "$tmp/squashfs-root" "$ENGINE_DIR"
    rm -rf -- "$old"
    printf '%s\n' "$ENGINE_FINGERPRINT" > "$ENGINE_MARKER.tmp.$$"
    mv "$ENGINE_MARKER.tmp.$$" "$ENGINE_MARKER"
    printf 'entrypoint: OpenRA cache is ready\n'
)

setup_content() (
    set -Eeuo pipefail
    local parent tmp zip old
    parent="$CONFIG_ROOT/Content"
    mkdir -p "$parent"
    tmp=$(mktemp -d "$parent/.cnc-content.tmp.XXXXXX")
    zip="$(mktemp /tmp/cnc-packages.XXXXXX.zip)"
    trap 'rm -rf -- "$tmp" "$zip"' EXIT

    printf 'entrypoint: downloading Tiberian Dawn content\n'
    curl --fail --location --retry 3 --retry-all-errors --silent --show-error \
        "$CNC_CONTENT_URL" --output "$zip"
    verify_sha256 "$CNC_CONTENT_SHA256" "$zip"
    unzip -q "$zip" -d "$tmp"
    [[ -s "$tmp/conquer.mix" ]] \
        || fail "CNC content archive did not contain conquer.mix"

    old="$parent/.cnc-content.previous.$$"
    if [[ -e "$CONTENT_DIR" || -L "$CONTENT_DIR" ]]; then
        mv "$CONTENT_DIR" "$old"
    fi
    mv "$tmp" "$CONTENT_DIR"
    rm -rf -- "$old"
    printf '%s\n' "$CONTENT_FINGERPRINT" > "$CONTENT_MARKER.tmp.$$"
    mv "$CONTENT_MARKER.tmp.$$" "$CONTENT_MARKER"
    printf 'entrypoint: Tiberian Dawn content cache is ready\n'
)

[[ "$(uname -m)" == x86_64 ]] \
    || fail "OpenRA's pinned AppImage is x86_64; this container requires amd64"

[[ "$PORT" =~ ^[0-9]+$ ]] && ((PORT >= 1 && PORT <= 65535)) \
    || fail "PORT must be an integer between 1 and 65535"

if engine_ready; then
    printf 'entrypoint: using cached OpenRA %s\n' "$OPENRA_RELEASE"
else
    setup_engine
fi

if content_ready; then
    printf 'entrypoint: using cached Tiberian Dawn content\n'
else
    setup_content
fi

exec marimo edit --headless --host 0.0.0.0 --port "$PORT" ora_widget.py
