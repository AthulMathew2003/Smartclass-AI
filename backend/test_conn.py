import psycopg

hosts = ['127.0.0.1', 'localhost', '::1']
passwords = ['smartclass123', 'smartclass123\n', 'smartclass123 ', 'Smartclass123', 'SMARTCLASS123', 'postgres']

for h in hosts:
    for pw in passwords:
        try:
            conn = psycopg.connect(f"dbname=postgres user=postgres password='{pw.strip()}' host={h} port=5432", connect_timeout=3)
            print(f"SUCCESS: host={h}, password='{pw.strip()}'")
            conn.close()
        except Exception as e:
            print(f"Failed host={h}, password='{pw.strip()}': {e}")
