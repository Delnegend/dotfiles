#!/bin/bash
set -e

BREW="/home/linuxbrew/.linuxbrew/bin/brew"

if [ ! -x "$BREW" ]; then
    echo "Installing Homebrew..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" < /dev/null
fi

for pkg in git git-lfs just zoxide starship; do
    if ! command -v "$pkg" &>/dev/null; then
        echo "Installing $pkg..."
        "$BREW" install "$pkg" -y
    fi
done

git lfs install

if [ ! -d "$HOME/dotfiles" ]; then
    echo "Cloning dotfiles..."
    git clone --depth=1 git@github.com:Delnegend/dotfiles.git "$HOME/dotfiles"
fi

cd "$HOME/dotfiles"

echo "Symlinking bash config..."
ln -sf "$HOME/dotfiles/.bashrc_custom" "$HOME/.bashrc"
[ -L "$HOME/.bashrc.d" ] || rm -rf "$HOME/.bashrc.d"
ln -sfn "$HOME/dotfiles/.bashrc.d" "$HOME/.bashrc.d"

echo "Done! Restart your shell or run: source ~/.bashrc"
