"""
Calculate Real Available IPs Script
This script calculates the actual available IP addresses in all subnets
"""

import mysql.connector
from mysql.connector import Error
import ipaddress

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '9371',
    'database': 'ipam_db'
}

def calculate_real_available_ips():
    """Calculate real available IPs based on subnet sizes"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        # Get all subnets and their usage
        cursor.execute("""
            SELECT 
                subnet,
                COUNT(*) as total_records,
                SUM(CASE WHEN status = 'used' THEN 1 ELSE 0 END) as used_count,
                SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) as reserved_count
            FROM ip_inventory 
            WHERE subnet IS NOT NULL AND subnet != ''
            GROUP BY subnet
        """)
        
        subnet_data = cursor.fetchall()
        
        total_subnet_space = 0
        total_used = 0
        total_reserved = 0
        total_real_available = 0
        
        subnet_analysis = []
        
        print("🔍 Analyzing subnet utilization...")
        print("="*80)
        
        for row in subnet_data:
            subnet = row['subnet']
            used_count = row['used_count'] or 0
            reserved_count = row['reserved_count'] or 0
            
            try:
                # Calculate actual subnet size
                network = ipaddress.ip_network(subnet, strict=False)
                
                # For /31 and /32, use special handling
                if network.prefixlen >= 31:
                    subnet_size = network.num_addresses
                else:
                    subnet_size = network.num_addresses - 2  # Exclude network and broadcast
                
                if subnet_size <= 0:
                    continue
                
                real_available = subnet_size - used_count - reserved_count
                utilization = (used_count / subnet_size * 100) if subnet_size > 0 else 0
                
                total_subnet_space += subnet_size
                total_used += used_count
                total_reserved += reserved_count
                total_real_available += real_available
                
                subnet_info = {
                    'subnet': subnet,
                    'size': subnet_size,
                    'used': used_count,
                    'reserved': reserved_count,
                    'available': real_available,
                    'utilization': round(utilization, 1),
                    'is_private': network.is_private
                }
                
                subnet_analysis.append(subnet_info)
                
                # Print only high utilization subnets or large subnets
                if utilization > 50 or subnet_size > 1000:
                    status = "🔴" if utilization > 80 else "🟡" if utilization > 50 else "🟢"
                    print(f"{status} {subnet:<18} | Size: {subnet_size:>6,} | Used: {used_count:>4} | Available: {real_available:>6,} | Util: {utilization:>5.1f}%")
                    
            except Exception as e:
                print(f"❌ Error processing subnet {subnet}: {e}")
                continue
        
        print("="*80)
        print(f"📊 SUMMARY:")
        print(f"   Total Subnet Space:  {total_subnet_space:,} IPs")
        print(f"   Total Used:          {total_used:,} IPs")
        print(f"   Total Reserved:      {total_reserved:,} IPs")  
        print(f"   Total Available:     {total_real_available:,} IPs")
        print(f"   Overall Utilization: {(total_used/total_subnet_space*100):.1f}%")
        print("="*80)
        
        # Show top 10 largest available subnets
        print(f"🔝 TOP 10 SUBNETS WITH MOST AVAILABLE IPs:")
        top_available = sorted(subnet_analysis, key=lambda x: x['available'], reverse=True)[:10]
        for subnet in top_available:
            print(f"   {subnet['subnet']:<18} | Available: {subnet['available']:>6,} IPs | Size: {subnet['size']:>6,} | Util: {subnet['utilization']:>5.1f}%")
        
        cursor.close()
        connection.close()
        
        return {
            'total_space': total_subnet_space,
            'total_used': total_used,
            'total_reserved': total_reserved,
            'total_available': total_real_available,
            'subnets_analyzed': len(subnet_analysis)
        }
        
    except Error as e:
        print(f"❌ Database error: {e}")
        return None

if __name__ == '__main__':
    print("🚀 Real IP Availability Calculator")
    print("="*80)
    
    result = calculate_real_available_ips()
    
    if result:
        print(f"\n✅ Analysis completed!")
        print(f"   Analyzed {result['subnets_analyzed']} subnets")
        print(f"   Found {result['total_available']:,} available IP addresses")
    else:
        print(f"\n❌ Analysis failed!")
