"""
Sample Data Generator for Network Sections IPAM System
This script creates sample network sections with subnets and IPs to test the multi-section functionality
"""

import mysql.connector
from mysql.connector import Error
import ipaddress
import random

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '9371',
    'database': 'ipam_db'
}

def get_db_connection():
    """Get database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"❌ Database connection error: {e}")
        return None

def create_sample_network_sections():
    """Create sample network sections data"""
    try:
        connection = get_db_connection()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Sample network sections
        sections = [
            ('Gi', 'All Gi Path Network', '#28a745'),
            ('True', 'True Corporation Network', '#dc3545'),
            ('Dtac', 'DTAC Network Infrastructure', '#fd7e14'),
            ('True-Online', 'True Online Services', '#20c997'),
            ('Public IP', 'Public IP Address Pool', '#6f42c1'),
            ('TESTBED', 'Testing Environment', '#ffc107'),
            ('CORE-NETWORK', 'Core Network Infrastructure', '#17a2b8'),
            ('RAN', 'Radio Access Network', '#6c757d')
        ]
        
        print("🔧 Creating sample network sections...")
        
        # Insert sections (ignore duplicates)
        for name, description, color in sections:
            try:
                cursor.execute("""
                    INSERT INTO network_sections (name, description, color) 
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE description = VALUES(description), color = VALUES(color)
                """, (name, description, color))
                print(f"✅ Created/Updated section: {name}")
            except Error as e:
                print(f"⚠️  Section {name} already exists or error: {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"❌ Error creating sections: {e}")
        return False

def create_sample_subnets():
    """Create sample subnets for each section"""
    try:
        connection = get_db_connection()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Get section IDs
        cursor.execute("SELECT id, name FROM network_sections")
        sections = {name: id for id, name in cursor.fetchall()}
        
        print("🔧 Creating sample subnets...")
        
        # Sample subnets for each section
        subnet_data = {
            'Gi': [
                ('10.0.0.0/24', 'Gi Management Network', '100', 'GI-VRF'),
                ('10.1.0.0/24', 'Gi User Network', '101', 'GI-VRF'),
                ('172.16.0.0/24', 'Gi Services Network', '102', 'GI-VRF')
            ],
            'True': [
                ('192.168.1.0/24', 'True Corporate LAN', '200', 'TRUE-VRF'),
                ('192.168.10.0/24', 'True Data Center', '210', 'TRUE-VRF'),
                ('10.10.0.0/16', 'True Internal Network', '220', 'TRUE-VRF')
            ],
            'Dtac': [
                ('172.20.0.0/24', 'DTAC Core Network', '300', 'DTAC-VRF'),
                ('172.21.0.0/24', 'DTAC RAN Network', '301', 'DTAC-VRF'),
                ('10.20.0.0/16', 'DTAC Services', '302', 'DTAC-VRF')
            ],
            'True-Online': [
                ('203.150.0.0/24', 'True Online Public', '400', 'ONLINE-VRF'),
                ('192.168.100.0/24', 'True Online Internal', '401', 'ONLINE-VRF')
            ],
            'Public IP': [
                ('203.154.0.0/24', 'Public Pool 1', '', 'INTERNET'),
                ('203.155.0.0/24', 'Public Pool 2', '', 'INTERNET')
            ],
            'TESTBED': [
                ('192.168.99.0/24', 'Test Network 1', '999', 'TEST-VRF'),
                ('10.99.0.0/24', 'Test Network 2', '998', 'TEST-VRF')
            ],
            'CORE-NETWORK': [
                ('10.0.1.0/24', 'Core Router Network', '501', 'CORE-VRF'),
                ('10.0.2.0/24', 'Core Switch Network', '502', 'CORE-VRF')
            ],
            'RAN': [
                ('10.128.0.0/16', 'RAN Primary Network', '600', 'RAN-VRF'),
                ('172.25.0.0/24', 'RAN Management', '601', 'RAN-VRF')
            ]
        }
        
        for section_name, subnets in subnet_data.items():
            if section_name in sections:
                section_id = sections[section_name]
                for subnet, description, vlan, vrf in subnets:
                    try:
                        cursor.execute("""
                            INSERT INTO subnets (subnet, description, section_id, vlan, vrf) 
                            VALUES (%s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE description = VALUES(description)
                        """, (subnet, description, section_id, vlan, vrf))
                        print(f"✅ Created subnet: {subnet} in {section_name}")
                    except Error as e:
                        print(f"⚠️  Subnet {subnet} already exists or error: {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"❌ Error creating subnets: {e}")
        return False

def create_sample_ips():
    """Create sample IP addresses for each section"""
    try:
        connection = get_db_connection()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Get sections and their subnets
        cursor.execute("""
            SELECT s.id, s.subnet, s.vrf, ns.id as section_id, ns.name as section_name
            FROM subnets s
            JOIN network_sections ns ON s.section_id = ns.id
        """)
        
        subnet_data = cursor.fetchall()
        
        print("🔧 Creating sample IP addresses...")
        
        statuses = ['used', 'available', 'reserved']
        
        for subnet_id, subnet_cidr, vrf, section_id, section_name in subnet_data:
            try:
                network = ipaddress.ip_network(subnet_cidr, strict=False)
                
                # Generate some sample IPs (first 10 addresses)
                ip_count = 0
                for ip in network.hosts():
                    if ip_count >= 10:  # Limit to first 10 IPs per subnet
                        break
                    
                    # Random status weighted towards 'used'
                    status = random.choices(statuses, weights=[60, 30, 10])[0]
                    
                    # Generate sample hostname for used IPs
                    hostname = ''
                    if status == 'used':
                        device_types = ['srv', 'rtr', 'sw', 'fw', 'lb']
                        hostname = f"{section_name.lower()}-{random.choice(device_types)}-{ip_count+1:02d}"
                    
                    # Sample description
                    descriptions = [
                        f"{section_name} network device",
                        f"Production server in {section_name}",
                        f"Network equipment - {section_name}",
                        f"Service endpoint - {section_name}",
                        ""
                    ]
                    description = random.choice(descriptions)
                    
                    try:
                        cursor.execute("""
                            INSERT INTO ip_inventory 
                            (ip_address, subnet, section_id, status, vrf_vpn, hostname, description)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (str(ip), subnet_cidr, section_id, status, vrf, hostname, description))
                        
                        ip_count += 1
                        
                    except Error as e:
                        # IP might already exist in this section
                        if "Duplicate entry" in str(e):
                            continue
                        else:
                            print(f"⚠️  Error adding IP {ip}: {e}")
                
                print(f"✅ Created {ip_count} IPs for subnet {subnet_cidr} in {section_name}")
                
            except Exception as e:
                print(f"❌ Error processing subnet {subnet_cidr}: {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        return True
        
    except Error as e:
        print(f"❌ Error creating IP addresses: {e}")
        return False

def main():
    """Main function to create all sample data"""
    print("🚀 Creating Sample Data for Network Sections IPAM System")
    print("=" * 60)
    
    # Create sample network sections
    if create_sample_network_sections():
        print("✅ Network sections created successfully")
    else:
        print("❌ Failed to create network sections")
        return
    
    # Create sample subnets
    if create_sample_subnets():
        print("✅ Subnets created successfully")
    else:
        print("❌ Failed to create subnets")
        return
    
    # Create sample IPs
    if create_sample_ips():
        print("✅ IP addresses created successfully")
    else:
        print("❌ Failed to create IP addresses")
        return
    
    print("=" * 60)
    print("🎉 Sample data creation completed!")
    print("\n📊 You can now test the Network Sections feature with:")
    print("   - 8 different network sections")
    print("   - Multiple subnets per section")
    print("   - Sample IP addresses with different statuses")
    print("   - Overlapping IP ranges across different sections")
    print("\n🌐 Open http://127.0.0.1:5005/network-sections to explore!")

if __name__ == "__main__":
    main()
