#!/usr/bin/env bash
# Usage: bash wait_agy.sh <pidfile> <timeout_sec> <output_path> [output_path2 ...]
# Waits for a detached background agy process until outputs are ready or timeout.
# Exits with 0 (OK), 1 (CRASH), 2 (TIMEOUT), or 3 (ERR: unreadable pidfile).

set -u

SECONDS=0
CHECK_INTERVAL=15
bad_output=""

# Check if a process is running and not a zombie
is_pid_alive() {
    local target_pid="$1"
    if ! kill -0 "$target_pid" 2>/dev/null; then
        return 1
    fi
    local state
    state="$(ps -p "$target_pid" -o state= 2>/dev/null | tr -d '[:space:]' || true)"
    if [ "$state" = "Z" ] || [ -z "$state" ]; then
        return 1
    fi
    return 0
}

# Check if any output path is invalid (missing or empty)
has_invalid_output() {
    bad_output=""
    for out in "${output_paths[@]}"; do
        if [ -z "$out" ] || [ ! -f "$out" ] || [ ! -s "$out" ]; then
            bad_output="${out:-empty-path}"
            return 0
        fi
    done
    return 1
}

# Success handler: print OK and tail up to 30 lines of log if present
handle_success() {
    echo "WAIT:OK elapsed=${SECONDS}s"
    if [ -f "$logfile" ]; then
        tail -n 30 "$logfile"
    fi
    exit 0
}

# PID termination handler: check output validity and log AGY_EXIT status
handle_pid_dead() {
    if has_invalid_output; then
        echo "WAIT:CRASH:$bad_output"
        exit 1
    fi

    if [ -f "$logfile" ]; then
        local agy_exit_line agy_exit_val
        agy_exit_line="$(grep -E '^[[:space:]]*AGY_EXIT=' "$logfile" 2>/dev/null | tail -n 1 || true)"
        if [ -n "$agy_exit_line" ]; then
            agy_exit_val="${agy_exit_line#*AGY_EXIT=}"
            agy_exit_val="$(echo "$agy_exit_val" | awk '{print $1}')"
            if [ "$agy_exit_val" != "0" ]; then
                echo "WAIT:CRASH:agy-exit-${agy_exit_val}"
                exit 1
            fi
        fi
    fi

    handle_success
}

# 1. pidfile 읽기. 파일 없음/빈 값/숫자 아님 → echo "WAIT:ERR:pidfile-unreadable"; exit 3
if [ "$#" -lt 3 ]; then
    echo "WAIT:ERR:pidfile-unreadable"
    exit 3
fi

pidfile="$1"
timeout_sec="$2"
shift 2
output_paths=("$@")

if [ ! -f "$pidfile" ]; then
    echo "WAIT:ERR:pidfile-unreadable"
    exit 3
fi

pid="$(tr -d '[:space:]' < "$pidfile" 2>/dev/null || true)"
if [ -z "$pid" ] || ! [[ "$pid" =~ ^[1-9][0-9]*$ ]]; then
    echo "WAIT:ERR:pidfile-unreadable"
    exit 3
fi

if ! [[ "$timeout_sec" =~ ^[0-9]+$ ]]; then
    echo "WAIT:ERR:pidfile-unreadable"
    exit 3
fi

# Determine logfile: <dir>/<pidfile without ext>.log
piddir="$(dirname "$pidfile")"
pidbase="$(basename "$pidfile")"
pidname="${pidbase%.*}"
logfile="${piddir}/${pidname}.log"

# 2. 이미 PID가 죽어있고 output들이 전부 유효하면 즉시 OK 처리 (빠른 경로)
if ! is_pid_alive "$pid"; then
    if ! has_invalid_output; then
        handle_success
    fi
fi

# 3. 루프 (15초 간격, elapsed < timeout)
while [ "$SECONDS" -lt "$timeout_sec" ]; do
    if ! is_pid_alive "$pid"; then
        handle_pid_dead
    fi

    echo "WAIT:running elapsed=${SECONDS}s" >&2

    remaining=$(( timeout_sec - SECONDS ))
    sleep_sec=$CHECK_INTERVAL
    if [ "$remaining" -lt "$sleep_sec" ]; then
        sleep_sec="$remaining"
    fi
    if [ "$sleep_sec" -gt 0 ]; then
        sleep "$sleep_sec"
    fi
done

# 루프 종료 후 PID 종료 여부 확인
if ! is_pid_alive "$pid"; then
    handle_pid_dead
fi

# 4. timeout 도달 → 20초 후 최종 재확인 1회
sleep 20

if is_pid_alive "$pid"; then
    echo "WAIT:TIMEOUT:process-still-running"
    exit 2
fi

handle_pid_dead
