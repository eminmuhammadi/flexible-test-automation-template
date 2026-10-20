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
    if [[ "$1" == -m || "$1" == --markexpr ]]; then
        if (( $# < 2 )); then
            echo "Missing expression after -m" >&2
            exit 2
        fi
        expression="$2"
        shift 2
    elif [[ "$1" == -m?* ]]; then
        expression="${1#-m}"
        shift
    elif [[ "$1" == --markexpr=* ]]; then
        expression="${1#--markexpr=}"
        shift
    else
        pytest_args+=("$1")
        shift
        continue
    fi
    if [[ -n "$marker" ]]; then
        marker="($marker) and ($expression)"
    else
        marker="$expression"
    fi
done

if [[ -n "$marker" ]]; then
    pytest_args=(-m "$marker" "${pytest_args[@]}")
fi
report_name="$(printf '%s' "$tag" | tr '[:upper:]' '[:lower:]')"
report_dir="reports/${report_name}/allure-results"
pytest_args+=("--alluredir=$report_dir" --clean-alluredir)
"$python_cmd" -m pytest "${pytest_args[@]}"
