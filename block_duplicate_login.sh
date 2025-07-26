#!/bin/bash


PORT_FILE="/root/monitor_users/ports.txt"

[ "$PAM_USER" = "root" ] && exit 0

allowed_port=$(grep "^$PAM_USER:" "$PORT_FILE" | cut -d':' -f2)

if [ -z "$allowed_port" ]; then

        exit 1
fi


session_count=$(ps aux | awk -v u="$PAM_USER" '$1 == u && $0 ~ ("sshd: " u)' | wc -l)

if [ "$session_count" -ge 2 ] && [ "$PAM_USER" != "ashkan" ]; then
    exit 1
fi

pids=$(ps aux | awk -v u="$PAM_USER" '$1 == "sshd" && $0 ~ ("sshd: " u) { print $2 }')

for pid in $pids; do
    port=$(sudo lsof -Panp "$pid" -i | awk '/TCP/ && /ESTABLISHED/ { split($9, a, ":"); split(a[2], b, "->"); print b[1] }')

    if [ "$port" != "$allowed_port" ]; then
        exit 1
    fi
done

exit 0