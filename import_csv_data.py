"""
Import Network Data from CSV to IPAM Database
Imports data from datalake.Inventory.port.csv into IPAM system
"""

import mysql.connector
from mysql.connector import Error
import csv
import ipaddress
from datetime import datetime
import re

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '9371',
    'database': 'ipam_db'
}

def extract_vrf_vpn(ifAlias, ifDescr):
    """Extract VRF/VPN information from interface alias and description"""
    text = f"{ifAlias or ''} {ifDescr or ''}".lower()
    
    # Look for VRF patterns
    vrf_patterns = [
        r'vrf[_\s]*([a-zA-Z0-9_\-]+)',
        r'vpn[_\s]*([a-zA-Z0-9_\-]+)',
        r'service[_\s]*([a-zA-Z0-9_\-]+)',
        r'tot[_\s]*([a-zA-Z0-9_\-]+)',
        r'cidvpn[_\s]*([a-zA-Z0-9_\-]+)'
    ]
    
    for pattern in vrf_patterns:
        match = re.search(pattern, text)
        if match:
            vrf_name = match.group(1).strip('_').strip()
            if len(vrf_name) > 2:  # Minimum length check
                return vrf_name.upper()
    
    # Check for domain/service indicators
    if 'service' in text:
        return 'SERVICE'
    elif 'billing' in text:
        return 'BILLING'
    elif 'oam' in text:
        return 'OAM'
    elif 'mgmt' in text or 'management' in text:
        return 'MGMT'
    elif 'tot' in text:
        return 'TOT'
    
    return None

def validate_ip(ip_str):
    """Validate IP address format"""
    if not ip_str or ip_str == '-' or ip_str.strip() == '':
        return None
    
    try:
        # Remove any extra whitespace
        ip_str = ip_str.strip()
        
        # Skip IPv6 addresses for now
        if ':' in ip_str and '.' not in ip_str:
            return None
            
        # Validate IPv4
        ipaddress.ip_address(ip_str)
        
        # Skip localhost and special addresses
        if ip_str.startswith('127.') or ip_str.startswith('169.254.'):
            return None
            
        return ip_str
    except ValueError:
        return None

def guess_subnet(ip_str):
    """Guess subnet based on IP address"""
    if not ip_str:
        return None
        
    try:
        ip = ipaddress.ip_address(ip_str)
        
        # Common subnet guessing based on IP ranges
        if ip_str.startswith('10.'):
            # Class A private - use /24 subnets
            parts = ip_str.split('.')
            return f"10.{parts[1]}.{parts[2]}.0/24"
        elif ip_str.startswith('192.168.'):
            # Class C private
            parts = ip_str.split('.')
            return f"192.168.{parts[2]}.0/24"
        elif ip_str.startswith('172.'):
            # Class B private
            parts = ip_str.split('.')
            second_octet = int(parts[1])
            if 16 <= second_octet <= 31:
                return f"172.{parts[1]}.{parts[2]}.0/24"
        
        # Default to /24 subnet
        parts = ip_str.split('.')
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        
    except Exception:
        return None

def determine_status(oper_status, admin_status, ip_address):
    """Determine IP status based on interface status"""
    if not ip_address:
        return 'available'
    
    # If interface is up and has IP, it's used
    if oper_status == 'Up' and admin_status == 'Up':
        return 'used'
    elif admin_status == 'Down':
        return 'reserved'  # Administratively down
    else:
        return 'available'

def import_csv_data():
    """Import data from CSV file"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Clear existing data
        print("🗑️ Clearing existing IP data...")
        cursor.execute("DELETE FROM ip_inventory")
        connection.commit()
        
        # Open and read CSV file
        print("📂 Reading CSV file...")
        imported_count = 0
        skipped_count = 0
        error_count = 0
        
        with open('datalake.Inventory.port.csv', 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            print("📊 Processing network interfaces...")
            
            # Track unique IPs to avoid duplicates
            seen_ips = set()
            
            for row_num, row in enumerate(reader, 1):
                if row_num % 10000 == 0:
                    print(f"   Processed {row_num:,} rows...")
                
                try:
                    # Extract relevant fields
                    ip_address = validate_ip(row.get('ifIP', ''))
                    
                    # Skip if no valid IP
                    if not ip_address or ip_address in seen_ips:
                        skipped_count += 1
                        continue
                    
                    seen_ips.add(ip_address)
                    
                    # Extract other fields
                    hostname = row.get('host_name', '').strip()
                    interface_name = row.get('ifName', '').strip()
                    interface_desc = row.get('ifDescr', '').strip()
                    interface_alias = row.get('ifAlias', '').strip()
                    vendor = row.get('vendor', '').strip()
                    model = row.get('model', '').strip()
                    domain = row.get('domain', '').strip()
                    
                    # Extract VRF/VPN information
                    vrf_vpn = extract_vrf_vpn(interface_alias, interface_desc)
                    
                    # Build hostname with domain if available
                    full_hostname = hostname
                    if domain and domain != hostname:
                        full_hostname = f"{hostname}.{domain}" if hostname else domain
                    
                    # Guess subnet
                    subnet = guess_subnet(ip_address)
                    
                    # Determine status
                    oper_status = row.get('ifOperStatus', '').strip()
                    admin_status = row.get('ifAdminStatus', '').strip()
                    status = determine_status(oper_status, admin_status, ip_address)
                    
                    # Build description
                    description_parts = []
                    if interface_name:
                        description_parts.append(f"Interface: {interface_name}")
                    if interface_desc and interface_desc != interface_name:
                        description_parts.append(f"Desc: {interface_desc}")
                    if vendor:
                        description_parts.append(f"Vendor: {vendor}")
                    if model:
                        description_parts.append(f"Model: {model}")
                    if oper_status and admin_status:
                        description_parts.append(f"Status: {admin_status}/{oper_status}")
                    
                    description = " | ".join(description_parts)
                    
                    # Insert into database
                    insert_query = """
                        INSERT INTO ip_inventory 
                        (ip_address, subnet, status, vrf_vpn, hostname, description)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    
                    values = (
                        ip_address,
                        subnet,
                        status,
                        vrf_vpn,
                        full_hostname[:100] if full_hostname else '',  # Limit hostname length
                        description[:500] if description else ''  # Limit description length
                    )
                    
                    cursor.execute(insert_query, values)
                    imported_count += 1
                    
                    # Commit every 1000 records for performance
                    if imported_count % 1000 == 0:
                        connection.commit()
                        
                except Exception as e:
                    error_count += 1
                    if error_count <= 10:  # Only show first 10 errors
                        print(f"   ⚠️ Error processing row {row_num}: {e}")
        
        # Final commit
        connection.commit()
        
        # Get statistics
        cursor.execute("SELECT status, COUNT(*) FROM ip_inventory GROUP BY status")
        stats = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(DISTINCT subnet) FROM ip_inventory WHERE subnet IS NOT NULL")
        subnet_count = cursor.fetchone()[0]
        
        print(f"\n✅ Import completed!")
        print(f"   📥 Imported: {imported_count:,} IP addresses")
        print(f"   ⏭️ Skipped: {skipped_count:,} records")
        print(f"   ❌ Errors: {error_count:,} records")
        print(f"   🌐 Subnets: {subnet_count:,} unique subnets")
        
        print(f"\n📊 Status Distribution:")
        for status, count in stats:
            print(f"   {status}: {count:,}")
        
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"❌ Database error: {e}")
    except FileNotFoundError:
        print(f"❌ CSV file 'datalake.Inventory.port.csv' not found")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    print("🚀 IPAM CSV Import Tool")
    print("="*50)
    print("Importing network interface data from CSV...")
    print("This may take several minutes for large files.")
    print("="*50)
    
    start_time = datetime.now()
    import_csv_data()
    end_time = datetime.now()
    
    duration = end_time - start_time
    print(f"\n⏱️ Import completed in {duration.total_seconds():.1f} seconds")
