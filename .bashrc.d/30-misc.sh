eval "$(starship init bash)"
eval "$(zoxide init bash --cmd cd)"

_dotfiles_pull() {
    local stamp=/tmp/dotfiles-last-success-pull
    local repo="$HOME/dotfiles"
    if [ -f "$stamp" ] && [ "$(( $(date +%s) - $(stat -c %Y "$stamp") ))" -lt 3600 ]; then
        return
    fi
    (
        local out rc
        out=$(cd "$repo" && git pull --rebase --autostash --ff-only 2>&1); rc=$?
        if [ $rc -eq 0 ]; then
            date +%s > "$stamp"
        else
            printf 'From dotfiles-pull %s\nSubject: dotfiles git pull failed\n\n%s\n' \
                "$(date)" "$out" >> /var/spool/mail/"$USER"
        fi
    ) &
    disown
}
_dotfiles_pull
unset _dotfiles_pull
