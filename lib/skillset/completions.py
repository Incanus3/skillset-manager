"""Emit native shell completion scripts for skillset."""

import sys


COMMANDS = "init create use rename remove list codex claude augment current show doctor skills completions"

BASH = rf"""_skillset_names() {{
    local output line
    output="$(command skillset list 2>/dev/null)" || return 0
    while IFS= read -r line; do
        line="${{line#\* }}"
        printf '%s\n' "${{line% \[m\]}}"
    done <<< "$output"
}}

_skillset_positional_count() {{
    local index token skip=0 after_options=0 count=0
    for ((index = 2; index < COMP_CWORD; index++)); do
        token="${{COMP_WORDS[index]}}"
        if (( skip )); then ((skip--)); continue; fi
        if (( after_options )); then ((count++)); continue; fi
        case "$token" in
            --) after_options=1 ;;
            -f) skip=1 ;;
            --from)
                if [[ "${{COMP_WORDS[index+1]}}" == = ]]; then skip=2; else skip=1; fi
                ;;
            --from=*) ;;
            -h|--help|--manual|--use|--yes|-v|--verbose|--fix|-g|--global|-l|--local) ;;
            -*) ;;
            *) ((count++)) ;;
        esac
    done
    printf '%s' "$count"
}}

_skillset_after_option_terminator() {{
    local index
    for ((index = 2; index < COMP_CWORD; index++)); do
        [[ "${{COMP_WORDS[index]}}" == -- ]] && return 0
    done
    return 1
}}

_skillset_completion() {{
    local current="${{2-${{COMP_WORDS[COMP_CWORD]}}}}"
    local previous="${{COMP_WORDS[COMP_CWORD-1]}}"
    local subcommand position candidates value after_terminator=0
    COMPREPLY=()
    if (( COMP_CWORD == 1 )); then
        COMPREPLY=( $(compgen -W '-h --help {COMMANDS}' -- "$current") )
        return
    fi
    subcommand="${{COMP_WORDS[1]}}"
    position="$(_skillset_positional_count)"
    if _skillset_after_option_terminator; then after_terminator=1; fi
    case "$subcommand" in
        create)
            if (( ! after_terminator )) && [[ "$previous" == -f || "$previous" == --from ]]; then
                COMPREPLY=( $(compgen -W "$(_skillset_names)" -- "$current") )
                return
            fi
            if (( ! after_terminator && COMP_CWORD >= 2 )) &&
                    [[ "$previous" == = && "${{COMP_WORDS[COMP_CWORD-2]}}" == --from ]]; then
                COMPREPLY=( $(compgen -W "$(_skillset_names)" -- "$current") )
                return
            fi
            if (( ! after_terminator )) && [[ "$current" == --from=* ]]; then
                value="${{current#--from=}}"
                COMPREPLY=( $(compgen -W "$(_skillset_names)" -- "$value") )
                COMPREPLY=( "${{COMPREPLY[@]/#/--from=}}" )
                return
            fi
            candidates=''
            if (( ! after_terminator )); then candidates='-h --help -f --from --manual --use'; fi
            ;;
        use|remove|show)
            candidates=''
            if (( ! after_terminator )); then candidates='-h --help'; fi
            if (( ! after_terminator )) && [[ "$subcommand" == remove ]]; then candidates+=' --yes'; fi
            if (( position == 0 )); then candidates+=" $(_skillset_names)"; fi
            ;;
        rename)
            candidates=''
            if (( ! after_terminator )); then candidates='-h --help'; fi
            if (( position == 0 )); then candidates+=" $(_skillset_names)"; fi
            ;;
        list)
            candidates=''
            if (( ! after_terminator )); then candidates='-h --help -v --verbose'; fi
            ;;
        codex|claude|augment)
            candidates=''
            if (( COMP_CWORD == 2 )); then
                if (( ! after_terminator )); then
                    candidates='-h --help enable disable list'
                    if [[ "$subcommand" == augment ]]; then candidates+=' skills'; fi
                fi
            else
                case "${{COMP_WORDS[2]}}" in
                    enable|disable)
                        if (( ! after_terminator )); then
                            candidates='-h --help -g --global -l --local'
                        fi
                        if (( position == 1 )); then
                            candidates+=" $(_skillset_names)"
                        fi
                        ;;
                    list)
                        if (( ! after_terminator )); then candidates='-h --help -v --verbose -g --global -l --local'; fi
                        ;;
                    skills)
                        if [[ "$subcommand" == augment ]]; then
                            if (( COMP_CWORD == 3 )); then
                                if (( ! after_terminator )); then candidates='-h --help list'; fi
                            elif [[ "${{COMP_WORDS[3]}}" == list ]]; then
                                if (( ! after_terminator )); then candidates='-h --help -v --verbose -g --global -l --local'; fi
                            fi
                        fi
                        ;;
                esac
            fi
            ;;
        completions)
            candidates=''
            if (( ! after_terminator )); then candidates='-h --help'; fi
            if (( position == 0 )); then candidates+=' bash zsh fish'; fi
            ;;
        init|current)
            candidates=''
            if (( ! after_terminator )); then candidates='-h --help'; fi
            ;;
        doctor)
            candidates=''
            if (( ! after_terminator )); then candidates='-h --help --fix'; fi
            ;;
        skills) return ;;
        *) return ;;
    esac
    COMPREPLY=( $(compgen -W "$candidates" -- "$current") )
}}
complete -F _skillset_completion skillset
"""

ZSH = r"""#compdef skillset
if (( ! $+functions[compdef] )); then
    autoload -Uz compinit && compinit
fi

_skillset_names() {
    local output line
    output="$(command skillset list 2>/dev/null)" || return 0
    while IFS= read -r line; do
        line="${line#\* }"
        print -r -- "${line% \[m\]}"
    done <<< "$output"
}

_skillset() {
    local context state state_descr line
    typeset -A opt_args
    _arguments -S -C \
        -A "-*" \
        '(-h --help)'{-h,--help}'[show help]' \
        '1:command:->command' \
        '*::argument:->arguments' && return 0

    case "$state" in
        command)
            local -a commands
            commands=(
                'init:adopt existing global skills'
                'create:create a skillset'
                'use:activate a skillset'
                'rename:rename a skillset'
                'remove:remove an inactive skillset'
                'list:list managed skillsets'
                'codex:manage Codex-enabled skillsets'
                'claude:manage Claude Code-enabled skillsets'
                'augment:manage Auggie-enabled skillsets'
                'current:print the active skillset name'
                'show:show skills in a skillset'
                'doctor:diagnose the managed layout'
                'skills:run managed upstream skills'
                'completions:emit a shell completion script'
            )
            _describe 'skillset command' commands
            ;;
        arguments)
            case "${words[1]}" in
                init)
                    _arguments -S '(-h --help)'{-h,--help}'[show help]' '1:name:' && return 0
                    ;;
                create)
                    _arguments -S \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '(-f --from --manual)'{-f,--from=}'[clone from an existing skillset]:source skillset:->skillsets' \
                        '(-f --from --manual)'--manual'[create a hand-managed skillset]' \
                        '--use[activate the created skillset]' \
                        '1:name:' && return 0
                    ;;
                use)
                    _arguments -S '(-h --help)'{-h,--help}'[show help]' '1:name:->skillsets' && return 0
                    ;;
                rename)
                    _arguments -S \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '1:old name:->skillsets' '2:new name:' && return 0
                    ;;
                remove)
                    _arguments -S \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '--yes[skip confirmation]' '1:name:->skillsets' && return 0
                    ;;
                list)
                    _arguments -S \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '(-v --verbose)'{-v,--verbose}'[show skill inventory]' && return 0
                    ;;
                codex)
                    if (( CURRENT == 2 )); then
                        _values 'Codex command' \
                            'enable:enable a skillset for Codex' \
                            'disable:disable a skillset for Codex' \
                            'list:list Codex-enabled skillsets'
                        return
                    fi
                    if [[ "${words[2]}" == enable || "${words[2]}" == disable ]]; then
                        _arguments -S \
                            '(-h --help)'{-h,--help}'[show help]' \
                            '(-g --global -l --local)'{-g,--global}'[manage global Codex skills]' \
                            '(-g --global -l --local)'{-l,--local}'[manage local Codex skills]' \
                            '1:name:->skillsets' && return 0
                    elif [[ "${words[2]}" == list ]]; then
                        _arguments -S \
                            '(-h --help)'{-h,--help}'[show help]' \
                            '(-g --global -l --local)'{-g,--global}'[list global Codex skills]' \
                            '(-g --global -l --local)'{-l,--local}'[list local Codex skills]' \
                            '(-v --verbose)'{-v,--verbose}'[show skill inventory]' && return 0
                    fi
                    ;;
                claude)
                    if (( CURRENT == 2 )); then
                        _values 'Claude Code command' \
                            'enable:enable a skillset for Claude Code' \
                            'disable:disable a skillset for Claude Code' \
                            'list:list Claude Code-enabled skillsets'
                        return
                    fi
                    if [[ "${words[2]}" == enable || "${words[2]}" == disable ]]; then
                        _arguments -S \
                            '(-h --help)'{-h,--help}'[show help]' \
                            '(-g --global -l --local)'{-g,--global}'[manage global Claude Code skills]' \
                            '(-g --global -l --local)'{-l,--local}'[manage local Claude Code skills]' \
                            '1:name:->skillsets' && return 0
                    elif [[ "${words[2]}" == list ]]; then
                        _arguments -S \
                            '(-h --help)'{-h,--help}'[show help]' \
                            '(-g --global -l --local)'{-g,--global}'[list global Claude Code skills]' \
                            '(-g --global -l --local)'{-l,--local}'[list local Claude Code skills]' \
                            '(-v --verbose)'{-v,--verbose}'[show skill inventory]' && return 0
                    fi
                    ;;
                augment)
                    if (( CURRENT == 2 )); then
                        _values 'Auggie command' \
                            '-h:show help' \
                            '--help:show help' \
                            'enable:enable a skillset for Auggie' \
                            'disable:disable a skillset for Auggie' \
                            'list:list Auggie-enabled skillsets' \
                            'skills:list effective Auggie skills'
                        return
                    fi
                    if [[ "${words[2]}" == enable || "${words[2]}" == disable ]]; then
                        local after_terminator
                        after_terminator=${words[(I)--]}
                        local -a options names
                        options=()
                        if (( ! after_terminator )); then
                            if (( ! ${words[(I)-h]} && ! ${words[(I)--help]} )); then
                                options+=('-h:show help' '--help:show help')
                            fi
                            if (( ! ${words[(I)-g]} && ! ${words[(I)--global]} &&
                                ! ${words[(I)-l]} && ! ${words[(I)--local]} )); then
                                options+=(
                                    '-g:manage global Auggie skills'
                                    '--global:manage global Auggie skills'
                                    '-l:manage local Auggie skills'
                                    '--local:manage local Auggie skills'
                                )
                            fi
                            _describe -t options 'option' options && return 0
                        fi
                        local index
                        for (( index = 3; index < CURRENT; index++ )); do
                            [[ "${words[index]}" != -* ]] && return
                        done
                        names=("${(@f)$(_skillset_names)}")
                        (( ${#names} )) && _describe 'skillset' names
                    elif [[ "${words[2]}" == list ]]; then
                        (( ${words[(I)--]} )) && return
                        local -a options
                        options=()
                        if (( ! ${words[(I)-h]} && ! ${words[(I)--help]} )); then
                            options+=('-h:show help' '--help:show help')
                        fi
                        if (( ! ${words[(I)-g]} && ! ${words[(I)--global]} &&
                            ! ${words[(I)-l]} && ! ${words[(I)--local]} )); then
                            options+=(
                                '-g:list global Auggie skills'
                                '--global:list global Auggie skills'
                                '-l:list local Auggie skills'
                                '--local:list local Auggie skills'
                            )
                        fi
                        if (( ! ${words[(I)-v]} && ! ${words[(I)--verbose]} )); then
                            options+=('-v:show skill inventory' '--verbose:show skill inventory')
                        fi
                        _describe -t options 'option' options && return 0
                    elif [[ "${words[2]}" == skills ]]; then
                        if (( CURRENT == 3 )); then
                            _values 'Auggie skills command' \
                                '-h:show help' \
                                '--help:show help' \
                                'list:list effective Auggie skills'
                            return
                        elif [[ "${words[3]}" == list ]]; then
                            (( ${words[(I)--]} )) && return
                            local -a list_options
                            list_options=(
                            )
                            if (( ! ${words[(I)-h]} && ! ${words[(I)--help]} )); then
                                list_options+=(
                                    '-h:show help'
                                    '--help:show help'
                                )
                            fi
                            if (( ! ${words[(I)-g]} && ! ${words[(I)--global]} &&
                                ! ${words[(I)-l]} && ! ${words[(I)--local]} )); then
                                list_options+=(
                                    '-g:Filter effective winners from all User roots'
                                    '--global:Filter effective winners from all User roots'
                                    '-l:Filter effective winners from all Workspace roots'
                                    '--local:Filter effective winners from all Workspace roots'
                                )
                            fi
                            if (( ! ${words[(I)-v]} && ! ${words[(I)--verbose]} )); then
                                list_options+=(
                                    '-v:show resolved skill paths'
                                    '--verbose:show resolved skill paths'
                                )
                            fi
                            _describe -t options 'option' list_options && return 0
                        fi
                    fi
                    ;;
                current)
                    _arguments -S '(-h --help)'{-h,--help}'[show help]' && return 0
                    ;;
                doctor)
                    _arguments -S \
                        '(-h --help)'{-h,--help}'[show help]' \
                        '--fix[create safe missing replacement files after confirmation]' && return 0
                    ;;
                show)
                    _arguments -S '(-h --help)'{-h,--help}'[show help]' '1::name:->skillsets' && return 0
                    ;;
                completions)
                    _arguments -S '(-h --help)'{-h,--help}'[show help]' '1:shell:(bash zsh fish)' && return 0
                    ;;
                skills) return 0 ;;
            esac
            if [[ "$state" == skillsets ]]; then
                local -a names
                names=("${(@f)$(_skillset_names)}")
                (( ${#names} )) && _describe 'skillset' names
            fi
            ;;
    esac
}

if [[ "${zsh_eval_context[-1]}" == loadautofunc ]]; then
    _skillset "$@"
else
    compdef _skillset skillset
fi
"""

FISH = """function __skillset_names
    set -l output (command skillset list 2>/dev/null)
    set -l list_status $status
    test $list_status -eq 0; or return 0
    test (count $output) -gt 0; or return 0
    string replace -r '^\\* ' '' $output | string replace -r ' \\[m\\]$' ''
end

function __skillset_needs_command
    set -l tokens (commandline -xpc)
    test (count $tokens) -eq 1
end

function __skillset_at_empty_token
    set -l token (commandline -ct)
    test -z "$token"
end

function __skillset_using_command
    set -l tokens (commandline -xpc)
    test (count $tokens) -ge 2; and test $tokens[2] = $argv[1]
end

function __skillset_using_codex_command
    set -l tokens (commandline -xpc)
    test (count $tokens) -ge 3; and test $tokens[3] = $argv[1]
end

function __skillset_using_claude_command
    set -l tokens (commandline -xpc)
    test (count $tokens) -ge 3; and test $tokens[3] = $argv[1]
end

function __skillset_using_augment_command
    set -l tokens (commandline -xpc)
    test (count $tokens) -ge 3; and test $tokens[3] = $argv[1]
end

function __skillset_using_augment_skills_command
    set -l tokens (commandline -xpc)
    test (count $tokens) -ge 4; and test $tokens[3] = skills; and test $tokens[4] = $argv[1]
end

function __skillset_positional_count
    set -l tokens (commandline -xpc)
    set -e tokens[1..2]
    set -l count 0
    set -l skip false
    set -l after_options false
    for token in $tokens
        if test $skip = true
            set skip false
            continue
        end
        if test $after_options = true
            set count (math $count + 1)
            continue
        end
        switch $token
            case --
                set after_options true
            case -f --from
                set skip true
            case '--from=*' -h --help --manual --use --yes -v --verbose --fix -g --global -l --local '-*'
            case '*'
                set count (math $count + 1)
        end
    end
    echo $count
end

function __skillset_at_position
    test (__skillset_positional_count) -eq $argv[1]
end

complete -c skillset -f
complete -c skillset -n __skillset_needs_command -s h -l help -d 'Show help'
complete -c skillset -n '__skillset_needs_command; and __skillset_at_empty_token' -a '-h --help' -d 'Show help'
complete -c skillset -n __skillset_needs_command -a init -d 'Adopt existing global skills'
complete -c skillset -n __skillset_needs_command -a create -d 'Create a skillset'
complete -c skillset -n __skillset_needs_command -a use -d 'Activate a skillset'
complete -c skillset -n __skillset_needs_command -a rename -d 'Rename a skillset'
complete -c skillset -n __skillset_needs_command -a remove -d 'Remove an inactive skillset'
complete -c skillset -n __skillset_needs_command -a list -d 'List managed skillsets'
complete -c skillset -n __skillset_needs_command -a codex -d 'Manage Codex-enabled skillsets'
complete -c skillset -n __skillset_needs_command -a claude -d 'Manage Claude Code-enabled skillsets'
complete -c skillset -n __skillset_needs_command -a augment -d 'Manage Auggie-enabled skillsets'
complete -c skillset -n __skillset_needs_command -a current -d 'Print the active skillset name'
complete -c skillset -n __skillset_needs_command -a show -d 'Show skills in a skillset'
complete -c skillset -n __skillset_needs_command -a doctor -d 'Diagnose the managed layout'
complete -c skillset -n __skillset_needs_command -a skills -d 'Run managed upstream skills'
complete -c skillset -n __skillset_needs_command -a completions -d 'Emit a shell completion script'

for subcommand in init create use rename remove list codex claude augment current show doctor completions
    complete -c skillset -n "__skillset_using_command $subcommand" -s h -l help -d 'Show help'
    complete -c skillset -n "__skillset_using_command $subcommand; and __skillset_at_empty_token" -a '-h --help' -d 'Show help'
end
complete -c skillset -n '__skillset_using_command create' -s f -l from -x -a '(__skillset_names)' -d 'Clone from a skillset'
complete -c skillset -n '__skillset_using_command create; and __skillset_at_empty_token' -a '-f --from' -d 'Clone from a skillset'
complete -c skillset -n '__skillset_using_command create' -l manual -d 'Create a hand-managed skillset'
complete -c skillset -n '__skillset_using_command create; and __skillset_at_empty_token' -a '--manual' -d 'Create a hand-managed skillset'
complete -c skillset -n '__skillset_using_command create' -l use -d 'Activate the created skillset'
complete -c skillset -n '__skillset_using_command create; and __skillset_at_empty_token' -a '--use' -d 'Activate the created skillset'
complete -c skillset -n '__skillset_using_command use; and __skillset_at_position 0' -a '(__skillset_names)'
complete -c skillset -n '__skillset_using_command rename; and __skillset_at_position 0' -a '(__skillset_names)'
complete -c skillset -n '__skillset_using_command remove; and __skillset_at_position 0' -a '(__skillset_names)'
complete -c skillset -n '__skillset_using_command remove' -l yes -d 'Skip confirmation'
complete -c skillset -n '__skillset_using_command remove; and __skillset_at_empty_token' -a '--yes' -d 'Skip confirmation'
complete -c skillset -n '__skillset_using_command list' -s v -l verbose -d 'Show skill inventory'
complete -c skillset -n '__skillset_using_command list; and __skillset_at_empty_token' -a '-v --verbose' -d 'Show skill inventory'
complete -c skillset -n '__skillset_using_command codex; and __skillset_at_position 0' -a 'enable disable list'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command enable; and __skillset_at_position 1' -a '(__skillset_names)'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command disable; and __skillset_at_position 1' -a '(__skillset_names)'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command enable' -s g -l global -d 'Manage global Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command enable' -s l -l local -d 'Manage local Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command enable; and __skillset_at_empty_token' -a '-g --global' -d 'Manage global Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command enable; and __skillset_at_empty_token' -a '-l --local' -d 'Manage local Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command disable' -s g -l global -d 'Manage global Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command disable' -s l -l local -d 'Manage local Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command disable; and __skillset_at_empty_token' -a '-g --global' -d 'Manage global Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command disable; and __skillset_at_empty_token' -a '-l --local' -d 'Manage local Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command list' -s v -l verbose -d 'Show skill inventory'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command list' -s g -l global -d 'List global Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command list' -s l -l local -d 'List local Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command list; and __skillset_at_empty_token' -a '-v --verbose' -d 'Show skill inventory'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command list; and __skillset_at_empty_token' -a '-g --global' -d 'List global Codex skills'
complete -c skillset -n '__skillset_using_command codex; and __skillset_using_codex_command list; and __skillset_at_empty_token' -a '-l --local' -d 'List local Codex skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_at_position 0' -a 'enable disable list'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command enable; and __skillset_at_position 1' -a '(__skillset_names)'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command disable; and __skillset_at_position 1' -a '(__skillset_names)'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command enable' -s g -l global -d 'Manage global Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command enable' -s l -l local -d 'Manage local Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command enable; and __skillset_at_empty_token' -a '-g --global' -d 'Manage global Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command enable; and __skillset_at_empty_token' -a '-l --local' -d 'Manage local Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command disable' -s g -l global -d 'Manage global Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command disable' -s l -l local -d 'Manage local Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command disable; and __skillset_at_empty_token' -a '-g --global' -d 'Manage global Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command disable; and __skillset_at_empty_token' -a '-l --local' -d 'Manage local Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command list' -s v -l verbose -d 'Show skill inventory'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command list' -s g -l global -d 'List global Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command list' -s l -l local -d 'List local Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command list; and __skillset_at_empty_token' -a '-v --verbose' -d 'Show skill inventory'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command list; and __skillset_at_empty_token' -a '-g --global' -d 'List global Claude Code skills'
complete -c skillset -n '__skillset_using_command claude; and __skillset_using_claude_command list; and __skillset_at_empty_token' -a '-l --local' -d 'List local Claude Code skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_at_position 0' -a 'enable disable list skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command enable; and __skillset_at_position 1' -a '(__skillset_names)'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command disable; and __skillset_at_position 1' -a '(__skillset_names)'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command enable' -s g -l global -d 'Manage global Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command enable' -s l -l local -d 'Manage local Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command enable; and __skillset_at_empty_token' -a '-g --global' -d 'Manage global Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command enable; and __skillset_at_empty_token' -a '-l --local' -d 'Manage local Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command disable' -s g -l global -d 'Manage global Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command disable' -s l -l local -d 'Manage local Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command disable; and __skillset_at_empty_token' -a '-g --global' -d 'Manage global Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command disable; and __skillset_at_empty_token' -a '-l --local' -d 'Manage local Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command list' -s v -l verbose -d 'Show skill inventory'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command list' -s g -l global -d 'List global Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command list' -s l -l local -d 'List local Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command list; and __skillset_at_empty_token' -a '-v --verbose' -d 'Show skill inventory'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command list; and __skillset_at_empty_token' -a '-g --global' -d 'List global Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command list; and __skillset_at_empty_token' -a '-l --local' -d 'List local Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_command skills; and __skillset_at_position 1' -a list -d 'List effective Auggie skills'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_skills_command list' -s v -l verbose -d 'Show resolved skill paths'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_skills_command list' -s g -l global -d 'Filter effective winners from all User roots'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_skills_command list' -s l -l local -d 'Filter effective winners from all Workspace roots'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_skills_command list; and __skillset_at_empty_token' -a '-v --verbose' -d 'Show resolved skill paths'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_skills_command list; and __skillset_at_empty_token' -a '-g --global' -d 'Filter effective winners from all User roots'
complete -c skillset -n '__skillset_using_command augment; and __skillset_using_augment_skills_command list; and __skillset_at_empty_token' -a '-l --local' -d 'Filter effective winners from all Workspace roots'
complete -c skillset -n '__skillset_using_command doctor' -l fix -d 'Create safe missing replacement files after confirmation'
complete -c skillset -n '__skillset_using_command doctor; and __skillset_at_empty_token' -a '--fix' -d 'Create safe missing replacement files after confirmation'
complete -c skillset -n '__skillset_using_command show; and __skillset_at_position 0' -a '(__skillset_names)'
complete -c skillset -n '__skillset_using_command completions; and __skillset_at_position 0' -a 'bash zsh fish'
"""

SCRIPTS = {"bash": BASH, "zsh": ZSH, "fish": FISH}


def emit_completions(shell, output=None):
    output = sys.stdout if output is None else output
    output.write(SCRIPTS[shell])
