eval "$(starship init bash)"
eval "$(zoxide init bash --cmd cd)"

[ -f /usr/share/bash-completion/bash_completion ] && source /usr/share/bash-completion/bash_completion

(
  cd ~/dotfiles || exit
  git fetch origin main 2>/dev/null
  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse origin/main)
  if [ "$LOCAL" != "$REMOTE" ]; then
    echo " dotfiles: updates available, pulling..."
    if git pull origin main 2>&1; then
      echo " dotfiles: updated successfully"
    else
      echo " dotfiles: update failed (merge conflict?) - run 'git pull' manually"
    fi
  fi
) &
disown
