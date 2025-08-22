#!/usr/bin/env python3
"""
Add sample data to test section statistics
"""

import mysql.connector
from mysql.connector import Error
import random

def get_db_connection():
    """Create database connection"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='ipam_database',
            user='root',
            password='1234'
        )
        return connection
    except Error as e:
        print(f"❌ Database connection error: {e}")
        return None

def add_sample_data():
    """Add sample IP addresses and subnets to sections"""
    try:
        connection = get_db_connection()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Get sections
        cursor.execute("SELECT id, name FROM network_sections")
        sections = cursor.fetchall()
        
        for section_id, section_name in sections:
            print(f"Adding sample data for section: {section_name} (ID: {section_id})")
            
            # Add sample subnets for some sections
            if section_name in ['Production', 'Development', 'Testing', 'DMZ']:
                subnet_count = {'Production': 15, 'Development': 8, 'Testing': 5, 'DMZ': 3}[section_name]
                
                for i in range(subnet_count):
                    subnet = f"192.168.{section_id + i * 10}.0/24"
                    cursor.execute("""
                        INSERT IGNORE INTO subnets (subnet, description, section_id, vlan, location, vrf)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (subnet, f"{section_name} Subnet {i+1}", section_id, 100 + i, "DC1", f"{section_name.upper()}-VRF"))
                
                # Add sample IP addresses
                ip_count = {'Production': 450, 'Development': 200, 'Testing': 100, 'DMZ': 75}[section_name]
                used_percentage = {'Production': 0.75, 'Development': 0.45, 'Testing': 0.30, 'DMZ': 0.60}[section_name]
                
                for i in range(ip_count):
                    ip_octets = f"192.168.{section_id}.{i % 254 + 1}"
                    
                    # Determine status based on usage percentage
                    if i < int(ip_count * used_percentage):
                        status = 'Used'
                    elif i < int(ip_count * (used_percentage + 0.1)):
                        status = 'Reserved'
                    else:
                        status = 'Available'
                    
                    hostname = f"{section_name.lower()}-{i+1:03d}" if status == 'Used' else None
                    description = f"{section_name} IP {i+1}"
                    
                    cursor.execute("""
                        INSERT IGNORE INTO ip_addresses (ip_address, hostname, status, description, section_id, owner)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (ip_octets, hostname, status, description, section_id, f"{section_name} Team"))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("✅ Sample data added successfully!")
        return True
        
    except Error as e:
        print(f"❌ Error adding sample data: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Adding sample data for section statistics...")
    add_sample_data()
    print("✅ Sample data addition completed!")
