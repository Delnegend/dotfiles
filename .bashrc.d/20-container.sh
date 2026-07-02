if [ -f /run/.containerenv ]; then
    alias pm="flatpak-spawn --host podman"
    alias podman="flatpak-spawn --host podman"
    export PATH=$PATH:/usr/local/go/bin
fi
