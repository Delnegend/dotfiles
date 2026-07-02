REPO := justfile_directory()

_default:
	@just --list

# Symlink all configs
all: gitconfig bashrc opencode zed vscode mpv easyeffects font justfile

# Agent skills
agents:
    ln -sfn {{REPO}}/.config/agents ~/.config/agents

# Git config
gitconfig:
	ln -sf {{REPO}}/.gitconfig ~/.gitconfig

# Shell config
bashrc:
	ln -sf {{REPO}}/.bashrc_custom ~/.bashrc_custom
	[ -L ~/.bashrc.d ] || rm -rf ~/.bashrc.d
	ln -sfn {{REPO}}/.bashrc.d ~/.bashrc.d

# opencode
opencode:
	mkdir -p ~/.config/opencode
	ln -sf {{REPO}}/.config/opencode.jsonc ~/.config/opencode/opencode.jsonc

# Zed editor
zed:
	mkdir -p ~/.config/zed
	ln -sf {{REPO}}/.config/zed.jsonc ~/.config/zed/settings.json

# VS Code
vscode:
	mkdir -p ~/.config/Code/User
	ln -sf {{REPO}}/.config/vscode/settings.jsonc ~/.config/Code/User/settings.json
	ln -sf {{REPO}}/.config/vscode/keybindings.jsonc ~/.config/Code/User/keybindings.json
	[ -L ~/.config/Code/User/snippets ] || rm -rf ~/.config/Code/User/snippets
	ln -sfn {{REPO}}/.config/vscode/snippets ~/.config/Code/User/snippets

# mpv (Flatpak)
mpv:
	mkdir -p ~/.var/app/io.mpv.Mpv/config
	[ -L ~/.var/app/io.mpv.Mpv/config/mpv ] || rm -rf ~/.var/app/io.mpv.Mpv/config/mpv
	ln -sfn {{REPO}}/.config/mpv ~/.var/app/io.mpv.Mpv/config/mpv

# Easy Effects (Flatpak)
easyeffects:
	mkdir -p ~/.var/app/com.github.wwmm.easyeffects/config
	[ -L ~/.var/app/com.github.wwmm.easyeffects/config/easyeffects ] || rm -rf ~/.var/app/com.github.wwmm.easyeffects/config/easyeffects
	ln -sfn {{REPO}}/.config/easyeffects ~/.var/app/com.github.wwmm.easyeffects/config/easyeffects

# Font config + fonts (idempotent)
font:
	#!/bin/bash
	set -e
	REPO="{{REPO}}"

	mkdir -p ~/.config/fontconfig
	ln -sf "$REPO/.config/fontconfig/fonts.conf" ~/.config/fontconfig/fonts.conf

	if [ ! -f ~/.local/share/fonts/IosevkaNerdFont-Regular.ttf ]; then
		curl -fsSLo /tmp/Iosevka.tar.xz https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/Iosevka.tar.xz
		echo "213ee24cda99ca84d0a8326de133e7e8b2baf9ba23659ce829f589f771d357d2  /tmp/Iosevka.tar.xz" | sha256sum -c
		tar -xJf /tmp/Iosevka.tar.xz -C /tmp/iosevka \
			IosevkaNerdFont-ExtraLight.ttf \
			IosevkaNerdFont-ExtraLightItalic.ttf \
			IosevkaNerdFont-Light.ttf \
			IosevkaNerdFont-LightItalic.ttf \
			IosevkaNerdFont-Italic.ttf \
			IosevkaNerdFont-Regular.ttf \
			IosevkaNerdFont-Bold.ttf \
			IosevkaNerdFont-BoldItalic.ttf
		mkdir -p ~/.local/share/fonts
		mv /tmp/iosevka/*.ttf ~/.local/share/fonts/
		rm -rf /tmp/Iosevka.tar.xz /tmp/iosevka
	else
		echo "Iosevka Nerd Font already installed"
	fi

	if [ ! -f ~/.local/share/fonts/NotoColorEmoji.ttf ]; then
		curl -fsSLo /tmp/NotoColorEmoji.ttf https://github.com/googlefonts/noto-emoji/raw/refs/heads/main/fonts/NotoColorEmoji.ttf
		echo "72a635cb3d2f3524c51620cdde406b217204e8a6a06c6a096ff8ed4b5fd6e27b  /tmp/NotoColorEmoji.ttf" | sha256sum -c
		mkdir -p ~/.local/share/fonts
		mv /tmp/NotoColorEmoji.ttf ~/.local/share/fonts/
	else
		echo "Noto Color Emoji already installed"
	fi

	fc-cache -f

# Dump current brew state to Brewfile
brew-dump:
	brew bundle dump --force --file={{REPO}}/Brewfile

# justfile itself
justfile:
	ln -sf {{REPO}}/.justfile_custom ~/.justfile
