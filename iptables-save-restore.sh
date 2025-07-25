#!/bin/bash

RULES_FILE="/etc/iptables/rules.v4"

case "$1" in
  save)
    iptables-save -c > "$RULES_FILE"
    ;;
  restore)
    if [[ -f "$RULES_FILE" ]]; then

      iptables-restore -c < "$RULES_FILE"
    else
      exit 1
    fi
    ;;
  *)
    exit 1
    ;;
esac