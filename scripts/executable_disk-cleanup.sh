#!/bin/bash
# Weekly disk cleanup (bazzite). Run by disk-cleanup.timer; force with:
#   systemctl --user start disk-cleanup.service
# Every step is independent: one failure is logged and the rest still run.
set -u
export PATH="$HOME/.local/bin:$HOME/.bun/bin:/home/linuxbrew/.linuxbrew/bin:$PATH"

failed=0
step() {
    echo "== $1"
    shift
    "$@" || { echo "!! step failed: exit $?"; failed=1; }
}

# Rust build output: every `target/` next to a Cargo.toml under ~/projects.
# `podman unshare` so files written by rootless devcontainers (subuid-owned) go too.
rust_targets() {
    local t
    find "$HOME/projects" \( -name node_modules -o -name .git \) -prune -o \
        -type d -name target -prune -print 2>/dev/null |
        while IFS= read -r t; do
            [ -f "$(dirname "$t")/Cargo.toml" ] || continue
            echo "rm $t ($(du -sh "$t" 2>/dev/null | cut -f1))"
            podman unshare rm -rf -- "$t"
        done
}

# Devcontainers: per project folder keep only the newest container; older
# stopped ones are removed (running ones are never touched).
devcontainer_dedupe() {
    podman ps -aq --filter label=devcontainer.local_folder |
        xargs -r podman inspect --format \
            '{{.Created.Unix}}|{{.ID}}|{{.Name}}|{{.State.Status}}|{{index .Config.Labels "devcontainer.local_folder"}}' |
        sed 's#|/var/home/#|/home/#' |
        sort -t'|' -k5,5 -k1,1nr |
        awk -F'|' 'seen[$5]++ && $4 != "running" { print $2, $3, $5 }' |
        while read -r id name folder; do
            echo "rm container $name ($folder)"
            podman rm -- "$id" >/dev/null
        done
}

download_caches() {
    if command -v uv >/dev/null; then uv cache clean; fi
    rm -rf -- "$HOME/.cache/Homebrew" "$HOME/.cache/pip" "$HOME/.npm/_cacache" \
        "$HOME/.bun/install/cache" "$HOME/.cache/AppImage-Cache" \
        "$HOME/.cache/BraveSoftware" "$HOME/.local/share/zed/external_agents"
}

# Trash: remove items deleted more than 30 days ago (freedesktop Trash spec).
old_trash() {
    local trash="${XDG_DATA_HOME:-$HOME/.local/share}/Trash"
    local cutoff info d t name
    cutoff=$(date -d '30 days ago' +%s)
    for info in "$trash"/info/*.trashinfo; do
        [ -e "$info" ] || continue
        d=$(sed -n 's/^DeletionDate=//p' "$info")
        t=$(date -d "$d" +%s 2>/dev/null) || continue
        ((t < cutoff)) || continue
        name=$(basename "$info" .trashinfo)
        rm -rf -- "$trash/files/$name" && rm -f -- "$info"
    done
}

df -h "$HOME" | tail -1
step "rust build output" rust_targets
step "devcontainer dedupe" devcontainer_dedupe
step "leftover image-build containers" buildah rm --all
step "unused container images" podman image prune -a -f --build-cache
step "unused container volumes" podman volume prune -f
step "download caches" download_caches
step "unused flatpak runtimes" flatpak uninstall --unused --noninteractive
step "trash older than 30 days" old_trash
df -h "$HOME" | tail -1
exit "$failed"
