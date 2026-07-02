export DOCKER_HOST="unix://$XDG_RUNTIME_DIR/podman/podman.sock"
echo >> "/home/$(whoami)/.profile"
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> "/home/$(whoami)/.profile"
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
