export DOCKER_HOST="unix://$XDG_RUNTIME_DIR/podman/podman.sock"
echo >> /home/$USER/.profile
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> /home/$USER/.profile
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
