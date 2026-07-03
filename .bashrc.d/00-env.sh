export DOCKER_HOST="unix://$XDG_RUNTIME_DIR/podman/podman.sock"
export PATH=/home/biolak/.opencode/bin:$PATH
echo >> "/home/$(whoami)/.profile"
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> "/home/$(whoami)/.profile"
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
