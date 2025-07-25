import mysql.connector
import subprocess

db_config = {
    'user': 'root',
    'password': 'aBc.123456',
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'monitor_users_db',
}

THRESHOLD_BYTES = 150 * 1024 * 1024 * 1024


def parse_size(size_str):
    size_str = size_str.strip().upper()
    if size_str.endswith('K'):
        return int(float(size_str[:-1]) * 1024)
    elif size_str.endswith('M'):
        return int(float(size_str[:-1]) * 1024 * 1024)
    elif size_str.endswith('G'):
        return int(float(size_str[:-1]) * 1024 * 1024 * 1024)
    else:
        return int(size_str)


def get_ports(cursor):
    cursor.execute("SELECT id, port FROM users")
    return cursor.fetchall()


def get_iptables_volume(port, direction):
    try:
        cmd = f"sudo iptables -L -v -n | grep {port} | grep {direction}"
        result = subprocess.check_output(cmd, shell=True, text=True)

        for line in result.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]
    except subprocess.CalledProcessError:
        pass
    return 0


def update_volumes(cursor, user_id, port, download_volume, upload_volume):
    sql = "UPDATE users SET download_volume = %s, upload_volume = %s WHERE id = %s"
    cursor.execute(sql, (download_volume, upload_volume, user_id))
    total = parse_size(download_volume) + parse_size(upload_volume)
    if total >= THRESHOLD_BYTES:
        subprocess.call(
            f"sudo iptables -D INPUT -p tcp --dport {port} -j ACCEPT", shell=True)
        subprocess.call(
            f"sudo iptables -D OUTPUT -p tcp --sport {port} -j ACCEPT", shell=True)
    subprocess.call(
        "sudo iptables-save -c > /etc/iptables/rules.v4", shell=True)


def main():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    users = get_ports(cursor)
    for user_id, port in users:
        download = get_iptables_volume(port, 'spt:')
        upload = get_iptables_volume(port, 'dpt:')
        update_volumes(cursor, user_id, port, download, upload)

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
