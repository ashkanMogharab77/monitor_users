#!/bin/bash

BLOCKED_FILE="/root/monitor_users/blocked_users_ips.txt"
PORT_FILE="/root/monitor_users/ports.txt"
port = "6040"

if ! grep -q "^$PAM_USER:" "$PORT_FILE"; then
    exit 0
fi

valid_sessions=$(grep "^$PAM_USER:" "$PORT_FILE" | cut -d':' -f2)
session_count=$(ps aux | awk -v u="$PAM_USER" '$1 == u && $0 ~ ("sshd: " u)' | wc -l)

if [ "$session_count" -ge "$valid_sessions" ]; then
    exit 1
fi

pids=$(ps aux | awk -v u="$PAM_USER" '$1 == "sshd" && $0 ~ ("sshd: " u) { print $2 }')

for pid in $pids; do
    ip=$(ss -tunp | grep "pid=$pid" | grep "$port" | awk '{print $6}' | cut -d':' -f1)
    while IFS=: read -r user line_ip; do
        if [[ "$user" == "$PAM_USER" && "$line_ip" == "$ip" ]]; then
            exit 1
        fi
    done < <(grep "$ip" "$BLOCKED_FILE")
done

exit 0