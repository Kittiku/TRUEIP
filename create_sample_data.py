"""
Sample Data Loader for IPAM System
"""

import mysql.connector
from mysql.connector import Error
import random
import ipaddress

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '9371',
    'database': 'ipam_db'
}

def create_sample_data():
    """Create sample IP data for testing"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM ip_inventory")
        print("🗑️ Cleared existing data")
        
        # Sample subnets
        subnets = [
            '192.168.1.0/24',
            '192.168.2.0/24',
            '10.0.1.0/24',
            '10.0.2.0/24',
            '172.16.1.0/24'
        ]
        
        # Sample hostnames
        hostnames = [
            'server01.example.com',
            'server02.example.com',
            'workstation01.example.com',
            'router01.example.com',
            'switch01.example.com',
            'firewall01.example.com',
            'database01.example.com',
            'web01.example.com',
            'mail01.example.com',
            'backup01.example.com'
        ]
        
        # Sample VRF/VPN
        vrfs = ['VRF-CORE', 'VRF-DMZ', 'VRF-MGMT', 'VPN-SITE1', 'VPN-SITE2', '']
        
        # Sample descriptions
        descriptions = [
            'Production server',
            'Development server',
            'Test environment',
            'Network infrastructure',
            'Security appliance',
            'Database server',
            'Web server',
            'Mail server',
            'Backup system',
            'Monitoring system'
        ]
        
        sample_data = []
        
        # Generate sample IPs for each subnet
        for subnet in subnets:
            network = ipaddress.ip_network(subnet)
            ip_count = min(50, network.num_addresses - 2)  # Limit to 50 IPs per subnet
            
            # Get first 50 usable IPs
            host_ips = list(network.hosts())[:ip_count]
            
            for ip in host_ips:
                status = random.choice(['used', 'available', 'reserved'])
                hostname = random.choice(hostnames) if status == 'used' else ''
                vrf = random.choice(vrfs)
                description = random.choice(descriptions) if status == 'used' else ''
                
                sample_data.append({
                    'ip_address': str(ip),
                    'subnet': subnet,
                    'status': status,
                    'vrf_vpn': vrf,
                    'hostname': hostname,
                    'description': description
                })
        
        # Insert sample data
        insert_query = """
            INSERT INTO ip_inventory 
            (ip_address, subnet, status, vrf_vpn, hostname, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        for data in sample_data:
            values = (
                data['ip_address'],
                data['subnet'],
                data['status'],
                data['vrf_vpn'],
                data['hostname'],
                data['description']
            )
            cursor.execute(insert_query, values)
        
        connection.commit()
        print(f"✅ Created {len(sample_data)} sample IP addresses")
        
        # Show statistics
        cursor.execute("SELECT status, COUNT(*) FROM ip_inventory GROUP BY status")
        stats = cursor.fetchall()
        print("\n📊 Sample Data Statistics:")
        for status, count in stats:
            print(f"   {status}: {count}")
        
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"❌ Error creating sample data: {e}")

if __name__ == '__main__':
    print("🚀 Creating sample data for IPAM system...")
    create_sample_data()
    print("✅ Sample data creation completed!")
