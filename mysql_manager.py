"""
MySQL Database Manager for IPAM System
Handles MySQL database operations for better performance and scalability
"""

import mysql.connector
from mysql.connector import Error
import pandas as pd
import json
from datetime import datetime
import os
import ipaddress

class MySQLManager:
    def __init__(self, host='localhost', user='root', password='9371', database='ipam_db'):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        
        self.create_database()
        self.connect()
        self.init_tables()
    
    def create_database(self):
        """Create database if it doesn't exist"""
        try:
            # Connect without specifying database
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            cursor = connection.cursor()
            
            # Create database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            print(f"✅ Database '{self.database}' created/verified")
            
            cursor.close()
            connection.close()
            
        except Error as e:
            print(f"❌ Error creating database: {e}")
    
    def connect(self):
        """Connect to MySQL database"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print(f"✅ Connected to MySQL database '{self.database}'")
            return True
            
        except Error as e:
            print(f"❌ Error connecting to MySQL: {e}")
            return False
    
    def init_tables(self):
        """Initialize database tables"""
        if not self.connection:
            return
            
        cursor = self.connection.cursor()
        
        try:
            # Network devices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS network_devices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device_id VARCHAR(50),
                    host_name VARCHAR(255),
                    ipaddress VARCHAR(45),
                    status VARCHAR(50),
                    vendor VARCHAR(100),
                    model VARCHAR(200),
                    ne_type VARCHAR(100),
                    domain VARCHAR(100),
                    site VARCHAR(200),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_ip (ipaddress),
                    INDEX idx_domain (domain),
                    INDEX idx_vendor (vendor)
                ) ENGINE=InnoDB
            ''')
            
            # Port interfaces table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS port_interfaces (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    port_id VARCHAR(50),
                    device_id VARCHAR(50),
                    interface_name VARCHAR(255),
                    interface_ip VARCHAR(45),
                    interface_status VARCHAR(50),
                    port_type VARCHAR(100),
                    hostname VARCHAR(255),
                    vendor VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_interface_ip (interface_ip),
                    INDEX idx_device_id (device_id),
                    INDEX idx_hostname (hostname)
                ) ENGINE=InnoDB
            ''')
            
            # IP assignments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_assignments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ip_address VARCHAR(45) UNIQUE,
                    device_id VARCHAR(50),
                    interface_id INT,
                    subnet VARCHAR(45),
                    assignment_type VARCHAR(50),
                    status VARCHAR(50),
                    hostname VARCHAR(255),
                    vendor VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_ip_address (ip_address),
                    INDEX idx_subnet (subnet),
                    INDEX idx_device_id (device_id)
                ) ENGINE=InnoDB
            ''')
            
            # Network tree cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS network_tree_cache (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tree_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            ''')
            
            # Statistics cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stats_cache (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    stats_data JSON,
                    cache_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_cache_type (cache_type)
                ) ENGINE=InnoDB
            ''')
            
            self.connection.commit()
            print("✅ Database tables initialized successfully")
            
        except Error as e:
            print(f"❌ Error creating tables: {e}")
        finally:
            cursor.close()
    
    def import_csv_data(self, devices_csv='datalake.Inventory.csv', ports_csv='datalake.Inventory.port.csv'):
        """Import data from CSV files to MySQL database"""
        if not self.connection:
            print("❌ No database connection")
            return
            
        cursor = self.connection.cursor()
        
        try:
            # Clear existing data
            print("🗑️ Clearing existing data...")
            cursor.execute('DELETE FROM ip_assignments')
            cursor.execute('DELETE FROM port_interfaces')
            cursor.execute('DELETE FROM network_devices')
            cursor.execute('DELETE FROM network_tree_cache')
            cursor.execute('DELETE FROM stats_cache')
            
            # Import network devices
            if os.path.exists(devices_csv):
                print(f"📥 Importing devices from {devices_csv}")
                devices_df = pd.read_csv(devices_csv)
                
                device_data = []
                for _, row in devices_df.iterrows():
                    device_data.append((
                        str(row.get('id', '')),
                        str(row.get('host_name', '')),
                        str(row.get('ipaddress', '')),
                        str(row.get('status', '')),
                        str(row.get('vendor', '')),
                        str(row.get('model', '')),
                        str(row.get('ne_type', '')),
                        str(row.get('domain', '')),
                        str(row.get('site', ''))
                    ))
                
                cursor.executemany('''
                    INSERT INTO network_devices 
                    (device_id, host_name, ipaddress, status, vendor, model, ne_type, domain, site)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', device_data)
                
                print(f"✅ Imported {len(device_data)} devices")
            
            # Import port interfaces and create devices from port data
            if os.path.exists(ports_csv):
                print(f"📥 Importing ports from {ports_csv}")
                # Read in chunks to handle large file
                chunk_size = 10000
                total_imported = 0
                device_map = {}  # Track unique devices
                
                for chunk in pd.read_csv(ports_csv, chunksize=chunk_size, dtype={'id': 'str'}, low_memory=False):
                    port_data = []
                    ip_assignments = []
                    
                    for _, row in chunk.iterrows():
                        # Create device entry from port data
                        hostname = str(row.get('host_name', ''))  # Fixed column name
                        vendor = str(row.get('vendor', ''))
                        device_id = str(row.get('host_id', ''))   # Use host_id as device_id
                        domain = str(row.get('domain', ''))
                        
                        if hostname and hostname != 'nan' and hostname not in device_map:
                            device_map[hostname] = {
                                'device_id': device_id,
                                'hostname': hostname,
                                'vendor': vendor,
                                'domain': domain,
                                'status': 'UP'  # Assume UP if in port data
                            }
                        
                        # Port interface data
                        port_data.append((
                            str(row.get('id', '')),
                            str(row.get('host_id', '')),        # Fixed column name
                            str(row.get('ifName', '')),         # Fixed column name
                            str(row.get('ifIP', '')),
                            str(row.get('ifOperStatus', '')),   # Fixed column name
                            str(row.get('ifType', '')),         # Fixed column name
                            hostname,
                            vendor
                        ))
                        
                        # Create IP assignment if valid IP
                        ip = str(row.get('ifIP', ''))
                        if ip and ip != 'nan' and ip != '' and ip != '-':
                            try:
                                ip_obj = ipaddress.IPv4Address(ip)
                                subnet = str(ipaddress.IPv4Network(f"{ip_obj}/24", strict=False))
                                
                                ip_assignments.append((
                                    str(ip_obj),
                                    str(row.get('host_id', '')),    # Fixed column name
                                    str(row.get('id', '')),
                                    subnet,
                                    'interface',
                                    'active',
                                    hostname,
                                    vendor
                                ))
                            except:
                                continue
                    
                    # Insert port data
                    if port_data:
                        cursor.executemany('''
                            INSERT INTO port_interfaces 
                            (port_id, device_id, interface_name, interface_ip, interface_status, port_type, hostname, vendor)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ''', port_data)
                    
                    # Insert IP assignments
                    if ip_assignments:
                        cursor.executemany('''
                            INSERT IGNORE INTO ip_assignments 
                            (ip_address, device_id, interface_id, subnet, assignment_type, status, hostname, vendor)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ''', ip_assignments)
                    
                    total_imported += len(port_data)
                    if total_imported % 50000 == 0:
                        print(f"📊 Imported {total_imported} port records...")
                
                print(f"✅ Completed importing {total_imported} port interfaces")
                
                # Import devices from port data
                if device_map:
                    device_data = []
                    for device in device_map.values():
                        device_data.append((
                            device['device_id'],
                            device['hostname'],
                            '',  # No IP address in main device table
                            device['status'],
                            device['vendor'],
                            '',  # model
                            '',  # ne_type
                            device['domain'],  # domain from port data
                            ''   # site
                        ))
                    
                    cursor.executemany('''
                        INSERT INTO network_devices 
                        (device_id, host_name, ipaddress, status, vendor, model, ne_type, domain, site)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', device_data)
                    
                    print(f"✅ Created {len(device_data)} network devices from port data")
            
            self.connection.commit()
            print("🎉 All data imported successfully!")
            
        except Error as e:
            print(f"❌ Error importing CSV data: {e}")
            self.connection.rollback()
        except Exception as e:
            print(f"❌ General error: {e}")
            self.connection.rollback()
        finally:
            cursor.close()
    
    def get_network_stats(self):
        """Get network statistics from database"""
        if not self.connection or not self.connection.is_connected():
            print("❌ MySQL connection lost, attempting to reconnect...")
            if not self.connect():
                return {'total_devices': 0, 'active_devices': 0, 'domains': 0, 'subnets': 0, 'vendor_distribution': {}}
            
        cursor = self.connection.cursor()
        
        try:
            # Check cache first
            cursor.execute('''
                SELECT stats_data FROM stats_cache 
                WHERE cache_type = 'network_stats' 
                AND created_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                ORDER BY created_at DESC LIMIT 1
            ''')
            
            cached = cursor.fetchone()
            if cached:
                return json.loads(cached[0])
            
            # Get device counts
            cursor.execute('SELECT COUNT(*) FROM network_devices')
            total_devices = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM network_devices WHERE status != 'DOWN' AND status IS NOT NULL AND status != ''")
            active_devices = cursor.fetchone()[0]
            
            # Get unique domains
            cursor.execute('SELECT COUNT(DISTINCT domain) FROM network_devices WHERE domain IS NOT NULL AND domain != ""')
            domains = cursor.fetchone()[0]
            
            # Get unique subnets
            cursor.execute('SELECT COUNT(DISTINCT subnet) FROM ip_assignments WHERE subnet IS NOT NULL AND subnet != ""')
            subnets = cursor.fetchone()[0]
            
            # Get vendor distribution
            cursor.execute('''
                SELECT vendor, COUNT(*) as count 
                FROM network_devices 
                WHERE vendor IS NOT NULL AND vendor != '' 
                GROUP BY vendor 
                ORDER BY count DESC
                LIMIT 10
            ''')
            vendor_dist = dict(cursor.fetchall())
            
            stats = {
                'total_devices': total_devices,
                'active_devices': active_devices,
                'domains': domains,
                'subnets': subnets,
                'vendor_distribution': vendor_dist
            }
            
            # Cache the result
            cursor.execute('''
                INSERT INTO stats_cache (stats_data, cache_type) 
                VALUES (%s, %s)
            ''', (json.dumps(stats), 'network_stats'))
            self.connection.commit()
            
            return stats
            
        except Error as e:
            print(f"❌ Error getting stats: {e}")
            return {}
        finally:
            cursor.close()
    
    def get_network_tree(self):
        """Get network tree structure from database"""
        if not self.connection:
            return {"name": "IPAM Network", "children": [], "count": 0}
            
        cursor = self.connection.cursor()
        
        try:
            # Check cache first
            cursor.execute('''
                SELECT tree_data FROM network_tree_cache 
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 10 MINUTE)
                ORDER BY created_at DESC LIMIT 1
            ''')
            
            cached = cursor.fetchone()
            if cached:
                return json.loads(cached[0])
            
            # Build tree from database
            tree = self._build_tree_from_db(cursor)
            
            # Cache the result
            cursor.execute('INSERT INTO network_tree_cache (tree_data) VALUES (%s)', 
                         (json.dumps(tree),))
            self.connection.commit()
            
            return tree
            
        except Error as e:
            print(f"❌ Error getting tree: {e}")
            return {"name": "IPAM Network", "children": [], "count": 0}
        finally:
            cursor.close()
    
    def _build_tree_from_db(self, cursor):
        """Build network tree from database data"""
        # Domain mapping
        domain_mapping = {
            'CORE/AGGREGATION': 'Core Network',
            'ACCESS': 'Access Network', 
            'DATACENTER': 'Data Center',
            'WAN': 'WAN Network',
            'CAMPUS': 'Campus Network',
            'METRO': 'Metro Network',
            'CUSTOMER': 'Customer Premise',
            'MGMT': 'Management Network'
        }
        
        # Get domain statistics
        cursor.execute('''
            SELECT 
                COALESCE(NULLIF(domain, ''), 'Unknown') as domain,
                COUNT(*) as device_count
            FROM network_devices 
            GROUP BY domain
        ''')
        
        domain_stats = cursor.fetchall()
        
        tree = {
            "name": "IPAM Network",
            "type": "root", 
            "id": "root",
            "children": [],
            "count": sum(count for _, count in domain_stats)
        }
        
        # Build categories
        categories = {}
        for domain, count in domain_stats:
            category = domain_mapping.get(domain, "Network Equipment")
            
            if category not in categories:
                categories[category] = {
                    "name": category,
                    "type": "category",
                    "id": category.lower().replace(' ', '_'),
                    "count": 0,
                    "children": []
                }
            
            categories[category]["count"] += count
        
        tree["children"] = list(categories.values())
        return tree
    
    def get_ip_conflicts(self):
        """Get IP address conflicts from database"""
        if not self.connection:
            return {'total_conflicts': 0, 'conflicts': []}
            
        cursor = self.connection.cursor()
        
        try:
            # Find duplicate IPs
            cursor.execute('''
                SELECT 
                    ip_address,
                    COUNT(*) as conflict_count,
                    GROUP_CONCAT(DISTINCT hostname SEPARATOR ', ') as hostnames,
                    GROUP_CONCAT(DISTINCT vendor SEPARATOR ', ') as vendors
                FROM ip_assignments 
                WHERE status = 'active' AND ip_address IS NOT NULL AND ip_address != ''
                GROUP BY ip_address 
                HAVING COUNT(*) > 1
                ORDER BY conflict_count DESC
                LIMIT 50
            ''')
            
            conflicts = cursor.fetchall()
            
            conflict_details = []
            for ip, count, hostnames, vendors in conflicts:
                conflict_details.append({
                    'ip': ip,
                    'count': count,
                    'hostnames': hostnames.split(', ') if hostnames else [],
                    'vendors': vendors.split(', ') if vendors else []
                })
            
            return {
                'total_conflicts': len(conflicts),
                'conflicts': conflict_details
            }
            
        except Error as e:
            print(f"❌ Error getting conflicts: {e}")
            return {'total_conflicts': 0, 'conflicts': []}
        finally:
            cursor.close()
    
    def get_port_analysis(self):
        """Get port IP analysis"""
        if not self.connection:
            return {}
            
        cursor = self.connection.cursor()
        
        try:
            # Get subnet analysis
            cursor.execute('''
                SELECT 
                    subnet,
                    COUNT(*) as ip_count,
                    COUNT(DISTINCT hostname) as device_count
                FROM ip_assignments 
                WHERE subnet IS NOT NULL AND subnet != ''
                GROUP BY subnet
                ORDER BY ip_count DESC
                LIMIT 20
            ''')
            
            subnets = []
            for subnet, ip_count, device_count in cursor.fetchall():
                subnets.append({
                    'subnet': subnet,
                    'ip_count': ip_count,
                    'device_count': device_count
                })
            
            return {'subnets': subnets}
            
        except Error as e:
            print(f"❌ Error getting port analysis: {e}")
            return {}
        finally:
            cursor.close()
    
    def clear_cache(self):
        """Clear cached data"""
        if not self.connection:
            return
            
        cursor = self.connection.cursor()
        try:
            cursor.execute('DELETE FROM network_tree_cache')
            cursor.execute('DELETE FROM stats_cache')
            self.connection.commit()
            print("✅ Cache cleared")
        except Error as e:
            print(f"❌ Error clearing cache: {e}")
        finally:
            cursor.close()
    
    def close_connection(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✅ MySQL connection closed")

# Test the MySQL manager
if __name__ == "__main__":
    print("🗄️ Initializing MySQL Database Manager...")
    
    try:
        db = MySQLManager()
        
        # Import CSV data
        print("\n📥 Starting CSV data import...")
        db.import_csv_data()
        
        # Test queries
        print("\n📊 Testing database queries...")
        stats = db.get_network_stats()
        print(f"Stats: {stats}")
        
        tree = db.get_network_tree()
        print(f"Tree nodes: {len(tree.get('children', []))}")
        
        conflicts = db.get_ip_conflicts()
        print(f"IP Conflicts: {conflicts['total_conflicts']}")
        
        print("\n🎉 MySQL database setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'db' in locals():
            db.close_connection()
