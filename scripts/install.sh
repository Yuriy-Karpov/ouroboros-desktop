#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
UV_INSTALL_DOCS_URL="https://docs.astral.sh/uv/getting-started/installation/"

if [ ! -t 0 ]; then
    echo "Interactive installer requires a TTY on stdin." >&2
    exit 1
fi

choose_mode_menu() {
    local labels=(
        "uv + .venv (recommended)"
        "global pip"
    )
    local values=("uv" "global")
    local selected=0
    local key=""
    local menu_lines=$(( ${#labels[@]} + 2 ))
    local green=$'\033[32m'
    local reset=$'\033[0m'

    printf "\033[?25l" >&2
    trap 'printf "\033[?25h" >&2' EXIT

    while true; do
        printf "Ouroboros installer\n" >&2
        printf "Select Python environment mode with Up/Down and press Enter:\n" >&2
        for i in "${!labels[@]}"; do
            if [ "$i" -eq "$selected" ]; then
                printf " ${green}● %s${reset}\n" "${labels[$i]}" >&2
            else
                printf " ○ %s\n" "${labels[$i]}" >&2
            fi
        done

        IFS= read -rsn1 key
        if [ "$key" = "" ]; then
            printf "\033[?25h" >&2
            trap - EXIT
            printf "%s\n" "${values[$selected]}"
            return
        fi

        if [ "$key" = $'\033' ]; then
            IFS= read -rsn2 key || true
            case "$key" in
                "[A")
                    selected=$(( (selected + ${#labels[@]} - 1) % ${#labels[@]} ))
                    ;;
                "[B")
                    selected=$(( (selected + 1) % ${#labels[@]} ))
                    ;;
            esac
        fi

        printf "\033[%dA" "$menu_lines" >&2
    done
}

MODE="$(choose_mode_menu)"
if [ "$MODE" = "uv" ] && ! command -v "${OUROBOROS_UV_BIN:-uv}" >/dev/null 2>&1; then
    echo "ERROR: uv is not installed on this system." >&2
    echo "Install uv first: $UV_INSTALL_DOCS_URL" >&2
    exit 1
fi
exec bash scripts/setup_python_env.sh "$MODE"
