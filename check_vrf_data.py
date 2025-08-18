import mysql.connector

try:
    # Connect to database
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='9371',
        database='ipam_db'
    )
    cursor = conn.cursor()
    
    print("=== Checking ip_inventory table structure ===")
    cursor.execute('DESCRIBE ip_inventory')
    columns = cursor.fetchall()
    for col in columns:
        print(f"Column: {col[0]}, Type: {col[1]}")
    
    print("\n=== Sample VRF/VPN data ===")
    cursor.execute('SELECT DISTINCT vrf_vpn FROM ip_inventory WHERE vrf_vpn IS NOT NULL AND vrf_vpn != "" LIMIT 10')
    vrf_data = cursor.fetchall()
    if vrf_data:
        for row in vrf_data:
            print(f"VRF/VPN: {row[0]}")
    else:
        print("No VRF/VPN data found")
    
    print("\n=== Count of records with VRF/VPN ===")
    cursor.execute('SELECT COUNT(*) FROM ip_inventory WHERE vrf_vpn IS NOT NULL AND vrf_vpn != ""')
    count = cursor.fetchone()[0]
    print(f"Records with VRF/VPN: {count}")
    
    cursor.execute('SELECT COUNT(*) FROM ip_inventory')
    total = cursor.fetchone()[0]
    print(f"Total records: {total}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
