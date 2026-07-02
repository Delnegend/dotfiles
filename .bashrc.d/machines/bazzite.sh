if [ -f /usr/share/bazzite-cli/bling.sh ]; then
    source /usr/share/bazzite-cli/bling.sh
fi

export SSH_AUTH_SOCK=/home/lava/.var/app/com.bitwarden.desktop/data/.bitwarden-ssh-agent.sock
export XMODIFIERS=@im=fcitx
export PATH=$PATH:/var/home/lava/bin/jdk-25.0.2+10-jre/bin/
