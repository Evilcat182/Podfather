_podfather_complete() {
    local cur prev words cword
    _init_completion || return

    local commands="build start stop remove backup"

    # Complete the subcommand itself
    if [[ $cword -eq 1 ]]; then
        COMPREPLY=($(compgen -W "$commands" -- "$cur"))
        return
    fi

    local subcmd="${words[1]}"

    case "$subcmd" in
        build)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "--start" -- "$cur"))
            else
                _filedir -d
            fi
            ;;
        start|stop)
            _filedir -d
            ;;
        remove)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "--confirm --keep-secrets --keep-volumes --keep-networks" -- "$cur"))
            else
                _filedir -d
            fi
            ;;
        backup)
            local backup_commands="create restore"
            if [[ $cword -eq 2 ]]; then
                COMPREPLY=($(compgen -W "$backup_commands" -- "$cur"))
                return
            fi
            local backup_subcmd="${words[2]}"
            case "$backup_subcmd" in
                create|restore)
                    if [[ "$prev" == "--file" ]]; then
                        _filedir
                    elif [[ "$cur" == -* ]]; then
                        COMPREPLY=($(compgen -W "--file" -- "$cur"))
                    else
                        _filedir -d
                    fi
                    ;;
            esac
            ;;
    esac
}

complete -F _podfather_complete podfather
