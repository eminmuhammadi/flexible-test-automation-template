#!/usr/bin/env bash
set -eo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

python_cmd="${PYTHON:-}"
if [[ -z "$python_cmd" ]]; then
    if [[ -x .venv/bin/python ]]; then
        python_cmd=.venv/bin/python
    elif command -v python >/dev/null 2>&1; then
        python_cmd=python
    else
        python_cmd=python3
    fi
fi

tag="${1:-all}"
if (( $# )); then shift; fi
if [[ "$tag" != all && ! "$tag" =~ ^[A-Za-z][A-Za-z0-9_-]*$ ]]; then
    echo "Usage: $0 [test-tag|all] [pytest options...]" >&2
    exit 2
fi

pytest_args=()
marker=""
if [[ "$tag" != all ]]; then
    marker="test_case(id='$tag')"
fi

while (( $# )); do
    if [[ "$1" == -m ]]; then
        if (( $# < 2 )); then
            echo "Missing expression after -m" >&2
            exit 2
        fi
        if [[ -n "$marker" ]]; then
            marker="($marker) and ($2)"
        else
            marker="$2"
        fi
        shift 2
    else
        pytest_args+=("$1")
        shift
    fi
done

if [[ -n "$marker" ]]; then
    pytest_args=(-m "$marker" "${pytest_args[@]}")
fi
report_name="$(printf '%s' "$tag" | tr '[:upper:]' '[:lower:]')"
report_dir="reports/${report_name}/allure-results"
collection_dir="$(mktemp -d "${TMPDIR:-/tmp}/qa-test-collection.XXXXXX")"
appium_pid=""

cleanup() {
    if [[ -n "$appium_pid" ]]; then
        kill "$appium_pid" 2>/dev/null || true
        wait "$appium_pid" 2>/dev/null || true
    fi
    rm -rf "$collection_dir"
}
trap cleanup EXIT

start_appium_if_needed() {
    local mobile_marker="mobile" collection_output collection_status server_url appium_config
    local host port base_path
    local -a appium_args=()

    if [[ -n "$marker" ]]; then
        mobile_marker="($marker) and mobile"
    fi
    set +e
    collection_output="$("$python_cmd" -m pytest --collect-only -q \
        "${pytest_args[@]}" -m "$mobile_marker" \
        --alluredir="$collection_dir" --clean-alluredir 2>&1)"
    collection_status=$?
    set -e
    if [[ $collection_status -ne 0 || "$collection_output" != *"::"* ]]; then
        return 0
    fi

    server_url="${APPIUM_SERVER_URL:-}"
    if [[ -z "$server_url" ]]; then
        server_url="$(PYTHONPATH="src:src/platform${PYTHONPATH:+:$PYTHONPATH}" \
            "$python_cmd" -c 'from config.settings import Settings; print(Settings.from_env().appium_server_url)')"
    fi
    server_url="${server_url%/}"
    if curl -fsS "${server_url}/status" >/dev/null 2>&1; then
        echo "Using Appium at ${server_url}"
        return 0
    fi
    appium_config="$("$python_cmd" - "$server_url" <<'PY'
import ipaddress
import sys
from urllib.parse import urlparse

url = urlparse(sys.argv[1])
host = url.hostname or ""
try:
    local = host.lower() == "localhost" or ipaddress.ip_address(host).is_loopback
except ValueError:
    local = False
if url.scheme != "http" or not local:
    raise SystemExit(1)
print(host, url.port or 80, url.path.rstrip("/"), sep="\t")
PY
)" || {
        echo "Appium is unavailable at ${server_url}; start the configured server first." >&2
        return 1
    }
    IFS=$'\t' read -r host port base_path <<< "$appium_config"
    if ! command -v appium >/dev/null 2>&1; then
        echo "Appium is not running and the 'appium' command is unavailable." >&2
        return 1
    fi

    appium_args=(--address "$host" --port "$port")
    if [[ -n "$base_path" ]]; then
        appium_args+=(--base-path "$base_path")
    fi
    mkdir -p reports
    appium "${appium_args[@]}" >reports/appium.log 2>&1 &
    appium_pid=$!
    for ((attempt = 0; attempt < 30; attempt++)); do
        if curl -fsS "${server_url}/status" >/dev/null 2>&1; then
            echo "Started Appium at ${server_url}"
            return 0
        fi
        if ! kill -0 "$appium_pid" 2>/dev/null; then
            echo "Appium exited during startup; see reports/appium.log" >&2
            return 1
        fi
        sleep 1
    done
    echo "Appium did not become ready; see reports/appium.log" >&2
    return 1
}

if [[ " ${pytest_args[*]} " != *" --collect-only "* ]]; then
    start_appium_if_needed || exit 2
fi
pytest_args+=("--alluredir=$report_dir" --clean-alluredir)
"$python_cmd" -m pytest "${pytest_args[@]}"
