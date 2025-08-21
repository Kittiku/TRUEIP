"""
IPAM System - Clean Version
Simple IP Address Management System
Only IP Management functionality
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
from mysql.connector import Error
import json
import ipaddress
from datetime import datetime
from datetime import datetime
import ipaddress

app = Flask(__name__)

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

def init_database():
    """Initialize database and tables"""
    try:
        # Create database if not exists
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.close()
        connection.close()
        
        # Connect to database and create tables
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            
            # Create IP inventory table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_inventory (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ip_address VARCHAR(15) NOT NULL UNIQUE,
                    subnet VARCHAR(18) NOT NULL,
                    status ENUM('used', 'available', 'reserved') DEFAULT 'available',
                    vrf_vpn VARCHAR(50),
                    hostname VARCHAR(100),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_ip_address (ip_address),
                    INDEX idx_subnet (subnet),
                    INDEX idx_status (status)
                )
            ''')
            
            # Create subnets management table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subnets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    subnet VARCHAR(18) NOT NULL UNIQUE,
                    description TEXT,
                    section VARCHAR(50),
                    vlan VARCHAR(50),
                    device VARCHAR(100),
                    nameservers TEXT,
                    master_subnet VARCHAR(18),
                    vrf VARCHAR(50),
                    customer VARCHAR(100),
                    location VARCHAR(100),
                    mark_as_pool BOOLEAN DEFAULT FALSE,
                    mark_as_full BOOLEAN DEFAULT FALSE,
                    threshold_percentage INT DEFAULT 80,
                    check_hosts_status BOOLEAN DEFAULT FALSE,
                    discover_new_hosts BOOLEAN DEFAULT FALSE,
                    resolve_dns_names BOOLEAN DEFAULT FALSE,
                    show_as_name BOOLEAN DEFAULT FALSE,
                    irr VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_subnet (subnet),
                    INDEX idx_section (section),
                    INDEX idx_vrf (vrf)
                )
            ''')
            
            connection.commit()
            cursor.close()
            connection.close()
            print("✅ Database initialized successfully")
            
    except Error as e:
        print(f"❌ Database initialization error: {e}")

def get_ip_data(limit=100):
    """Get IP data from database"""
    try:
        connection = get_db_connection()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT 
                id, ip_address, subnet, status, vrf_vpn, hostname, 
                description, created_at, updated_at
            FROM ip_inventory 
            ORDER BY INET_ATON(ip_address)
            LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        # Convert datetime objects to strings
        for row in results:
            if row['created_at']:
                row['created_at'] = row['created_at'].isoformat()
            if row['updated_at']:
                row['updated_at'] = row['updated_at'].isoformat()
        
        cursor.close()
        connection.close()
        
        return results
        
    except Error as e:
        print(f"❌ Error getting IP data: {e}")
        return []

def get_real_statistics():
    """Get real IP statistics with calculated available IPs from subnet sizes"""
    try:
        connection = get_db_connection()
        if not connection:
            return {}
            
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
                
                total_subnet_space += subnet_size
                total_used += used_count
                total_reserved += reserved_count
                total_real_available += real_available
                    
            except Exception as e:
                print(f"Error processing subnet {subnet}: {e}")
                continue
        
        # Get total unique subnets
        cursor.execute("SELECT COUNT(DISTINCT subnet) as count FROM ip_inventory WHERE subnet IS NOT NULL")
        subnet_result = cursor.fetchone()
        total_subnets = subnet_result['count'] if subnet_result else 0
        
        cursor.close()
        connection.close()
        
        return {
            'total_ips': total_subnet_space,
            'used_ips': total_used,
            'reserved_ips': total_reserved,
            'available_ips': total_real_available,
            'total_subnets': total_subnets,
            'utilization_percent': round((total_used / total_subnet_space * 100), 2) if total_subnet_space > 0 else 0
        }
        
    except Error as e:
        print(f"❌ Error getting real statistics: {e}")
        return {}

def get_statistics():
    """Get IP statistics (legacy - shows only database counts)"""
    try:
        connection = get_db_connection()
        if not connection:
            return {}
            
        cursor = connection.cursor(dictionary=True)
        
        # Total IPs
        cursor.execute("SELECT COUNT(*) as total FROM ip_inventory")
        total_result = cursor.fetchone()
        total_ips = total_result['total'] if total_result else 0
        
        # Status counts
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as count
            FROM ip_inventory 
            GROUP BY status
        """)
        
        status_counts = cursor.fetchall()
        stats = {
            'total_ips': total_ips,
            'used_ips': 0,
            'available_ips': 0,
            'reserved_ips': 0
        }
        
        for row in status_counts:
            if row['status'] == 'used':
                stats['used_ips'] = row['count']
            elif row['status'] == 'available':
                stats['available_ips'] = row['count']
            elif row['status'] == 'reserved':
                stats['reserved_ips'] = row['count']
        
        # Subnets count
        cursor.execute("SELECT COUNT(DISTINCT subnet) as subnets FROM ip_inventory")
        subnet_result = cursor.fetchone()
        stats['total_subnets'] = subnet_result['subnets'] if subnet_result else 0
        
        cursor.close()
        connection.close()
        
        return stats
        
    except Error as e:
        print(f"❌ Error getting statistics: {e}")
        return {}

# Routes
@app.route('/')
def index():
    """Advanced IP Management Homepage"""
    return render_template('ip_management_clean.html')

@app.route('/ip-management')
def ip_management():
    """Advanced IP Management page"""
    return render_template('ip_management_clean.html')

@app.route('/ip-management-advanced')
def ip_management_advanced():
    """Advanced IP Management page with full features"""
    return render_template('ip_management_clean.html')

@app.route('/advanced-dashboard')
def advanced_dashboard():
    """Advanced Dashboard with charts and analytics"""
    return render_template('advanced_dashboard.html')

@app.route('/test-dashboard')  
def test_dashboard():
    """Test Dashboard for debugging"""
    return render_template('test_dashboard.html')

@app.route('/api/ip-data')
def api_ip_data():
    """API to get IP data"""
    try:
        limit = request.args.get('limit', 100, type=int)
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        
        # Calculate offset
        offset = (page - 1) * limit
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Build query with filters
        where_conditions = []
        params = []
        
        if search:
            where_conditions.append("(ip_address LIKE %s OR hostname LIKE %s OR description LIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
            
        if status_filter:
            where_conditions.append("status = %s")
            params.append(status_filter)
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get data
        query = f"""
            SELECT 
                id, ip_address, subnet, status, vrf_vpn, hostname, 
                description, created_at, updated_at
            FROM ip_inventory 
            {where_clause}
            ORDER BY INET_ATON(ip_address)
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM ip_inventory {where_clause}"
        cursor.execute(count_query, params[:-2] if params else [])  # Exclude limit and offset
        total_result = cursor.fetchone()
        total_count = total_result['total'] if total_result else 0
        
        # Convert datetime objects to strings
        for row in results:
            if row['created_at']:
                row['created_at'] = row['created_at'].isoformat()
            if row['updated_at']:
                row['updated_at'] = row['updated_at'].isoformat()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'data': results,
            'total': total_count,
            'page': page,
            'limit': limit,
            'total_pages': (total_count + limit - 1) // limit
        })
        
    except Error as e:
        print(f"❌ Error in API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics')
def api_statistics():
    """API to get statistics with accurate available IP calculation"""
    print("📊 Getting accurate statistics...")
    
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get status counts from existing data
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as count
            FROM ip_inventory 
            WHERE status IN ('used', 'available', 'reserved')
            GROUP BY status
        """)
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Get all unique subnets with their CIDR
        cursor.execute("""
            SELECT DISTINCT subnet 
            FROM ip_inventory 
            WHERE subnet IS NOT NULL AND subnet != ''
        """)
        subnets = [row['subnet'] for row in cursor.fetchall()]
        
        # Calculate total possible IPs and actual available IPs
        total_possible_ips = 0
        used_ips_count = status_counts.get('used', 0)
        reserved_ips_count = status_counts.get('reserved', 0)
        
        for subnet in subnets:
            try:
                import ipaddress
                network = ipaddress.IPv4Network(subnet, strict=False)
                # Get number of host IPs (excluding network and broadcast)
                possible_hosts = network.num_addresses - 2  # -2 for network and broadcast
                if possible_hosts > 0:
                    total_possible_ips += possible_hosts
            except:
                continue
        
        # Calculate actual available IPs
        actual_available_ips = total_possible_ips - used_ips_count - reserved_ips_count
        
        # Get total subnets count
        total_subnets = len(subnets)
        
        # Get Service Domain counts
        cursor.execute("SELECT COUNT(DISTINCT vrf_vpn) as count FROM ip_inventory WHERE vrf_vpn IS NOT NULL AND vrf_vpn != ''")
        total_vrfs = cursor.fetchone()['count']
        
        cursor.close()
        connection.close()
        
        stats = {
            'total_possible_ips': total_possible_ips,
            'used_ips': used_ips_count,
            'available_ips': actual_available_ips,
            'reserved_ips': reserved_ips_count,
            'total_ips_in_db': sum(status_counts.values()),
            'total_subnets': total_subnets,
            'total_vrfs': total_vrfs,
            'utilization_percentage': round((used_ips_count / total_possible_ips * 100), 2) if total_possible_ips > 0 else 0
        }
        
        print(f"📊 Accurate Stats: Total Possible={total_possible_ips}, Used={used_ips_count}, Available={actual_available_ips}")
        return jsonify(stats)
        
    except Error as e:
        print(f"❌ Error getting statistics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subnet-analysis')
def api_subnet_analysis():
    """API: Analyze subnet utilization"""
    try:
        subnet = request.args.get('subnet', '').strip()
        if not subnet:
            return jsonify({'error': 'Subnet parameter is required'}), 400
        
        # Validate subnet format
        try:
            network = ipaddress.ip_network(subnet, strict=False)
        except ValueError:
            return jsonify({'error': 'Invalid subnet format'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all IPs in this subnet from database
        cursor.execute("""
            SELECT ip_address, hostname, description, status, vrf_vpn, created_at, updated_at
            FROM ip_inventory 
            WHERE subnet = %s OR ip_address LIKE %s
            ORDER BY INET_ATON(ip_address)
        """, (subnet, f"{str(network.network_address).rsplit('.', 1)[0]}%"))
        
        used_ips = cursor.fetchall()
        cursor.close()
        connection.close()
        
        # Convert used IPs to dict for quick lookup
        used_ip_dict = {}
        for ip_data in used_ips:
            used_ip_dict[ip_data['ip_address']] = ip_data
        
        # Generate all possible IPs in subnet
        all_ips = []
        for ip in network.hosts():
            ip_str = str(ip)
            if ip_str in used_ip_dict:
                # IP is used
                ip_info = used_ip_dict[ip_str]
                all_ips.append({
                    'ip_address': ip_str,
                    'status': ip_info['status'],
                    'hostname': ip_info['hostname'] or '',
                    'description': ip_info['description'] or '',
                    'vrf_vpn': ip_info['vrf_vpn'] or '',
                    'created_at': ip_info['created_at'].isoformat() if ip_info['created_at'] else '',
                    'updated_at': ip_info['updated_at'].isoformat() if ip_info['updated_at'] else ''
                })
            else:
                # IP is available
                all_ips.append({
                    'ip_address': ip_str,
                    'status': 'available',
                    'hostname': '',
                    'description': '',
                    'vrf_vpn': '',
                    'created_at': '',
                    'updated_at': ''
                })
        
        # Calculate statistics
        total_ips = len(list(network.hosts()))
        used_count = len([ip for ip in all_ips if ip['status'] in ['used', 'reserved']])
        available_count = total_ips - used_count
        utilization = (used_count / total_ips * 100) if total_ips > 0 else 0
        
        result = {
            'subnet': subnet,
            'network_address': str(network.network_address),
            'broadcast_address': str(network.broadcast_address),
            'subnet_mask': str(network.netmask),
            'total_ips': total_ips,
            'used_ips': used_count,
            'available_ips': available_count,
            'utilization_percent': round(utilization, 2),
            'ip_list': all_ips
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ip-list')
def api_ip_list():
    """API to get paginated IP list with filtering"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        offset = (page - 1) * per_page
        
        # Get filter parameters
        subnet_filter = request.args.get('subnet', '')
        status_filter = request.args.get('status', '')
        vrf_filter = request.args.get('vrf', '')
        
        # Build WHERE clause
        where_conditions = ["1=1"]
        params = []
        
        if subnet_filter:
            where_conditions.append("subnet LIKE %s")
            params.append(f"%{subnet_filter}%")
            
        if status_filter:
            where_conditions.append("status = %s")
            params.append(status_filter)
            
        if vrf_filter:
            where_conditions.append("vrf_vpn LIKE %s")
            params.append(f"%{vrf_filter}%")
        
        where_clause = " AND ".join(where_conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM ip_inventory WHERE {where_clause}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']
        
        # Get IP data
        data_query = f"""
            SELECT id, ip_address, subnet, status, hostname, description, vrf_vpn, 
                   created_at, updated_at 
            FROM ip_inventory 
            WHERE {where_clause}
            ORDER BY INET_ATON(ip_address)
            LIMIT %s OFFSET %s
        """
        cursor.execute(data_query, params + [per_page, offset])
        ips = cursor.fetchall()
        
        # Format dates
        for ip in ips:
            if ip['created_at']:
                ip['created_at'] = ip['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if ip['updated_at']:
                ip['updated_at'] = ip['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'ips': ips,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            },
            'filters': {
                'subnet': subnet_filter,
                'status': status_filter,
                'vrf': vrf_filter
            }
        })
        
    except Error as e:
        print(f"❌ Error getting IP list: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/add-ip', methods=['POST'])
def api_add_ip():
    """API to add new IP"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['ip_address', 'subnet', 'status']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate IP address
        try:
            ipaddress.ip_address(data['ip_address'])
        except ValueError:
            return jsonify({'error': 'Invalid IP address format'}), 400
        
        # Validate subnet
        try:
            ipaddress.ip_network(data['subnet'], strict=False)
        except ValueError:
            return jsonify({'error': 'Invalid subnet format'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        
        # Check if IP already exists
        cursor.execute("SELECT id FROM ip_inventory WHERE ip_address = %s", (data['ip_address'],))
        if cursor.fetchone():
            cursor.close()
            connection.close()
            return jsonify({'error': 'IP address already exists'}), 409
        
        # Insert new IP
        insert_query = """
            INSERT INTO ip_inventory 
            (ip_address, subnet, status, vrf_vpn, hostname, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        values = (
            data['ip_address'],
            data['subnet'],
            data['status'],
            data.get('vrf_vpn', ''),
            data.get('hostname', ''),
            data.get('description', '')
        )
        
        cursor.execute(insert_query, values)
        connection.commit()
        
        new_id = cursor.lastrowid
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'id': new_id, 'message': 'IP added successfully'})
        
    except Error as e:
        print(f"❌ Error adding IP: {e}")
        return jsonify({'error': str(e)}), 500

# ================== ADVANCED SUBNET ANALYSIS API ==================
@app.route('/api/subnets-overview')
def api_subnets_overview():
    """API to get overview of all subnets with filtering"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get CIDR filter if provided
        cidr_filter = request.args.get('cidr', '')
        
        # Build query based on filter
        base_query = """
            SELECT 
                subnet,
                COUNT(*) as used_ips,
                SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) as reserved_ips,
                GROUP_CONCAT(DISTINCT vrf_vpn) as vrfs
            FROM ip_inventory 
            WHERE subnet IS NOT NULL AND subnet != '' AND status IN ('used', 'reserved')
        """
        
        if cidr_filter:
            base_query += f" AND subnet LIKE '%{cidr_filter}'"
            
        base_query += """
            GROUP BY subnet
            ORDER BY subnet
            LIMIT 100
        """
        
        cursor.execute(base_query)
        subnet_data = cursor.fetchall()
        
        # Calculate subnet capacity and available IPs using ipaddress library
        import ipaddress
        
        subnets = []
        for subnet_info in subnet_data:
            subnet = subnet_info['subnet']
            
            try:
                # Calculate total possible IPs in subnet
                network = ipaddress.IPv4Network(subnet, strict=False)
                total_possible_ips = network.num_addresses
                
                # For /30 and smaller subnets, subtract network and broadcast
                if network.prefixlen >= 30:
                    usable_ips = total_possible_ips - 2 if total_possible_ips > 2 else total_possible_ips
                else:
                    # For larger subnets, subtract network and broadcast addresses
                    usable_ips = total_possible_ips - 2
                
                used_ips = subnet_info['used_ips'] - (subnet_info['reserved_ips'] or 0)  # Don't double count reserved
                reserved_ips = subnet_info['reserved_ips'] or 0
                available_ips = max(0, usable_ips - used_ips - reserved_ips)
                
                # Calculate utilization
                if usable_ips > 0:
                    utilization = round(((used_ips + reserved_ips) / usable_ips) * 100, 1)
                else:
                    utilization = 100.0
                
                # Determine IP type
                subnet_ip = subnet.split('/')[0]
                if subnet_ip.startswith('10.') or subnet_ip.startswith('192.168.') or \
                   (subnet_ip.startswith('172.') and 16 <= int(subnet_ip.split('.')[1]) <= 31):
                    ip_type = 'private'
                else:
                    ip_type = 'public'
                
                subnets.append({
                    'subnet': subnet,
                    'total_ips': usable_ips,
                    'used_ips': used_ips,
                    'available_ips': available_ips,
                    'reserved_ips': reserved_ips,
                    'utilization': utilization,
                    'ip_type': ip_type,
                    'vrfs': subnet_info['vrfs']
                })
                
            except ValueError as e:
                print(f"⚠️ Invalid subnet format {subnet}: {e}")
                continue
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'subnets': subnets,
            'total_subnets': len(subnets),
            'cidr_filter': cidr_filter
        })
        
    except Error as e:
        print(f"❌ Error getting subnets overview: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subnet-detail/<path:subnet>')
def api_subnet_detail(subnet):
    """API to get detailed IP information for a specific subnet"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all IPs in the subnet from database
        cursor.execute("""
            SELECT ip_address, status, hostname, description, vrf_vpn, 
                   created_at, updated_at
            FROM ip_inventory 
            WHERE subnet = %s
            ORDER BY INET_ATON(ip_address)
        """, (subnet,))
        
        existing_ips = {row['ip_address']: row for row in cursor.fetchall()}
        
        # Calculate subnet capacity using ipaddress library
        import ipaddress
        try:
            network = ipaddress.IPv4Network(subnet, strict=False)
            all_ips = []
            
            # Generate all possible IPs in subnet
            for ip in network.hosts():
                ip_str = str(ip)
                if ip_str in existing_ips:
                    # IP exists in database
                    ip_data = existing_ips[ip_str]
                    
                    # Parse interface and device from description
                    description = ip_data['description'] or ''
                    interface_name = ''
                    device_name = ip_data['hostname'] or ''
                    
                    # Extract interface from description if available
                    if 'Interface:' in description:
                        try:
                            interface_part = description.split('Interface:')[1].split('|')[0].strip()
                            interface_name = interface_part
                        except:
                            interface_name = ''
                    
                    ip_data['interface_name'] = interface_name
                    ip_data['device_name'] = device_name
                    ip_data['created_at'] = ip_data['created_at'].strftime('%Y-%m-%d %H:%M:%S') if ip_data['created_at'] else ''
                    ip_data['updated_at'] = ip_data['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if ip_data['updated_at'] else ''
                    all_ips.append(ip_data)
                else:
                    # IP is available
                    all_ips.append({
                        'ip_address': ip_str,
                        'status': 'available',
                        'hostname': '',
                        'description': '',
                        'vrf_vpn': '',
                        'interface_name': '',
                        'device_name': '',
                        'created_at': '',
                        'updated_at': ''
                    })
            
            # Calculate statistics
            total_ips = len(list(network.hosts()))
            used_count = len([ip for ip in all_ips if ip['status'] in ['used', 'reserved']])
            available_count = total_ips - used_count
            utilization = (used_count / total_ips * 100) if total_ips > 0 else 0
            
            # Get VRF summary
            vrf_summary = {}
            for ip in all_ips:
                if ip['vrf_vpn'] and ip['status'] in ['used', 'reserved']:
                    vrf = ip['vrf_vpn']
                    if vrf not in vrf_summary:
                        vrf_summary[vrf] = {'used': 0, 'reserved': 0}
                    vrf_summary[vrf][ip['status']] += 1
            
            result = {
                'subnet': subnet,
                'network_address': str(network.network_address),
                'broadcast_address': str(network.broadcast_address),
                'subnet_mask': str(network.netmask),
                'prefix_length': network.prefixlen,
                'total_ips': total_ips,
                'used_ips': len([ip for ip in all_ips if ip['status'] == 'used']),
                'reserved_ips': len([ip for ip in all_ips if ip['status'] == 'reserved']),
                'available_ips': available_count,
                'utilization_percent': round(utilization, 2),
                'ip_list': all_ips,
                'vrf_summary': vrf_summary
            }
            
            cursor.close()
            connection.close()
            return jsonify(result)
            
        except ValueError as e:
            return jsonify({'error': f'Invalid subnet format: {e}'}), 400
        
    except Error as e:
        print(f"❌ Error getting subnet detail: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vrf-monitoring')
def api_vrf_monitoring():
    """API to get VRF monitoring data with IP statistics"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get Service Domain monitoring data
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN vrf_vpn IS NULL OR vrf_vpn = '' THEN 'No Service Domain'
                    ELSE vrf_vpn 
                END as vrf_name,
                COUNT(*) as total_ips,
                SUM(CASE WHEN status = 'used' THEN 1 ELSE 0 END) as used_ips,
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available_ips,
                SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) as reserved_ips,
                COUNT(DISTINCT subnet) as subnet_count,
                COUNT(DISTINCT hostname) as device_count,
                GROUP_CONCAT(DISTINCT subnet ORDER BY subnet) as subnets,
                MAX(updated_at) as last_update
            FROM ip_inventory 
            GROUP BY vrf_name
            HAVING total_ips > 0
            ORDER BY total_ips DESC
        """)
        
        vrf_data = cursor.fetchall()
        
        # Calculate additional metrics
        for vrf in vrf_data:
            if vrf['total_ips'] > 0:
                vrf['utilization_percentage'] = round((vrf['used_ips'] / vrf['total_ips']) * 100, 2)
            else:
                vrf['utilization_percentage'] = 0
                
            # Format last update
            if vrf['last_update']:
                vrf['last_update'] = vrf['last_update'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                vrf['last_update'] = 'Never'
                
            # Parse subnets
            if vrf['subnets']:
                vrf['subnet_list'] = vrf['subnets'].split(',')[:5]  # Show first 5 subnets
                vrf['has_more_subnets'] = len(vrf['subnets'].split(',')) > 5
            else:
                vrf['subnet_list'] = []
                vrf['has_more_subnets'] = False
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'vrf_data': vrf_data,
            'total_vrfs': len(vrf_data),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Error as e:
        print(f"❌ Error getting VRF monitoring data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-ip/<int:ip_id>', methods=['PUT'])
def api_update_ip(ip_id):
    """API to update IP"""
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        
        # Check if IP exists
        cursor.execute("SELECT id FROM ip_inventory WHERE id = %s", (ip_id,))
        if not cursor.fetchone():
            cursor.close()
            connection.close()
            return jsonify({'error': 'IP not found'}), 404
        
        # Build update query
        update_fields = []
        values = []
        
        updatable_fields = ['ip_address', 'subnet', 'status', 'vrf_vpn', 'hostname', 'description']
        for field in updatable_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                values.append(data[field])
        
        if not update_fields:
            cursor.close()
            connection.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        # Validate IP address if provided
        if 'ip_address' in data:
            try:
                ipaddress.ip_address(data['ip_address'])
            except ValueError:
                cursor.close()
                connection.close()
                return jsonify({'error': 'Invalid IP address format'}), 400
        
        # Validate subnet if provided
        if 'subnet' in data:
            try:
                ipaddress.ip_network(data['subnet'], strict=False)
            except ValueError:
                cursor.close()
                connection.close()
                return jsonify({'error': 'Invalid subnet format'}), 400
        
        values.append(ip_id)
        update_query = f"UPDATE ip_inventory SET {', '.join(update_fields)} WHERE id = %s"
        
        cursor.execute(update_query, values)
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'message': 'IP updated successfully'})
        
    except Error as e:
        print(f"❌ Error updating IP: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-ip/<int:ip_id>', methods=['DELETE'])
def api_delete_ip(ip_id):
    """API to delete IP"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        
        # Check if IP exists
        cursor.execute("SELECT id FROM ip_inventory WHERE id = %s", (ip_id,))
        if not cursor.fetchone():
            cursor.close()
            connection.close()
            return jsonify({'error': 'IP not found'}), 404
        
        # Delete IP
        cursor.execute("DELETE FROM ip_inventory WHERE id = %s", (ip_id,))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'message': 'IP deleted successfully'})
        
    except Error as e:
        print(f"❌ Error deleting IP: {e}")
        return jsonify({'error': str(e)}), 500

# ================== ADVANCED DASHBOARD API ROUTES ==================
@app.route('/api/charts-data')
def get_charts_data():
    """Get data for charts in advanced dashboard"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get status distribution
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM ip_inventory 
            GROUP BY status
        """)
        status_data = cursor.fetchall()
        
        # Get Service Domain distribution
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN vrf_vpn IS NULL OR vrf_vpn = '' THEN 'No Service Domain'
                    ELSE vrf_vpn 
                END as vrf_name,
                COUNT(*) as count 
            FROM ip_inventory 
            GROUP BY vrf_name
            ORDER BY count DESC
            LIMIT 10
        """)
        vrf_data = cursor.fetchall()
        
        # Get subnet distribution
        cursor.execute("""
            SELECT subnet, COUNT(*) as count 
            FROM ip_inventory 
            GROUP BY subnet
            ORDER BY count DESC
            LIMIT 10
        """)
        subnet_data = cursor.fetchall()
        
        # Get recent activity (last 7 days)
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count
            FROM ip_inventory 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        activity_data = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'status_distribution': status_data,
            'vrf_distribution': vrf_data,
            'subnet_distribution': subnet_data,
            'recent_activity': activity_data
        })
        
    except Error as e:
        print(f"❌ Error getting charts data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/network-tree')
def get_network_tree():
    """Get network tree data organized by Service Domain"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get tree structure grouped by VRF and subnet
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN vrf_vpn IS NULL OR vrf_vpn = '' THEN 'Default'
                    ELSE vrf_vpn 
                END as vrf_name,
                subnet,
                status,
                COUNT(*) as count
            FROM ip_inventory 
            GROUP BY vrf_name, subnet, status
            ORDER BY vrf_name, subnet, status
        """)
        
        raw_data = cursor.fetchall()
        cursor.close()
        connection.close()
        
        # Organize data into tree structure
        tree_data = {}
        
        for row in raw_data:
            vrf_name = row['vrf_name']
            subnet = row['subnet']
            status = row['status']
            count = row['count']
            
            if vrf_name not in tree_data:
                tree_data[vrf_name] = {}
            
            if subnet not in tree_data[vrf_name]:
                tree_data[vrf_name][subnet] = {}
            
            tree_data[vrf_name][subnet][status] = count
        
        return jsonify(tree_data)
        
    except Error as e:
        print(f"❌ Error getting network tree: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vrf-vpn-analysis')
def get_vrf_vpn_analysis():
    """Get Service Domain analysis data"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get detailed Service Domain statistics
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN vrf_vpn IS NULL OR vrf_vpn = '' THEN 'No Service Domain'
                    ELSE vrf_vpn 
                END as vrf_name,
                COUNT(*) as total_ips,
                SUM(CASE WHEN status = 'used' THEN 1 ELSE 0 END) as used_ips,
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available_ips,
                SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) as reserved_ips,
                COUNT(DISTINCT subnet) as subnet_count
            FROM ip_inventory 
            GROUP BY vrf_name
            ORDER BY total_ips DESC
        """)
        
        vrf_analysis = cursor.fetchall()
        
        # Calculate utilization percentages
        for vrf in vrf_analysis:
            if vrf['total_ips'] > 0:
                vrf['utilization_percentage'] = round((vrf['used_ips'] / vrf['total_ips']) * 100, 2)
            else:
                vrf['utilization_percentage'] = 0
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'vrf_analysis': vrf_analysis,
            'total_vrfs': len(vrf_analysis)
        })
        
    except Error as e:
        print(f"❌ Error getting Service Domain analysis: {e}")
        return jsonify({'error': str(e)}), 500

# ================== IP MANAGEMENT API ROUTES ==================
@app.route('/api/ipam/ip-conflicts')
def get_ip_conflicts():
    """Get IP address conflicts for IP Management page"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Find IP conflicts (same IP used multiple times)
        cursor.execute("""
            SELECT 
                ip_address,
                COUNT(*) as conflict_count,
                GROUP_CONCAT(
                    CONCAT(hostname, ' (', vrf_vpn, ')')
                    SEPARATOR ', '
                ) as usage_details
            FROM ip_inventory 
            WHERE ip_address IS NOT NULL AND ip_address != ''
            GROUP BY ip_address
            HAVING COUNT(*) > 1
            ORDER BY conflict_count DESC
            LIMIT 50
        """)
        
        conflicts_raw = cursor.fetchall()
        
        # Format conflicts data
        conflicts = []
        for conflict in conflicts_raw:
            usage_list = []
            if conflict['usage_details']:
                usage_details = conflict['usage_details'].split(', ')
                for detail in usage_details:
                    if '(' in detail and ')' in detail:
                        host = detail.split(' (')[0]
                        interface = detail.split(' (')[1].replace(')', '')
                        usage_list.append({
                            'host_name': host,
                            'interface': interface
                        })
            
            conflicts.append({
                'ip': conflict['ip_address'],
                'conflict_count': conflict['conflict_count'],
                'usage': usage_list
            })
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'conflicts': conflicts,
            'total_conflicts': len(conflicts)
        })
        
    except Error as e:
        print(f"❌ Error getting IP conflicts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ipam/port-ips')
def get_port_ips():
    """Get port IP analysis for IP Management page"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get subnet analysis
        cursor.execute("""
            SELECT 
                subnet,
                COUNT(*) as ip_count,
                COUNT(DISTINCT hostname) as device_count
            FROM ip_inventory 
            WHERE subnet IS NOT NULL AND subnet != ''
            GROUP BY subnet
            ORDER BY ip_count DESC
            LIMIT 20
        """)
        
        subnets = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            'subnets': subnets
        })
        
    except Error as e:
        print(f"❌ Error getting port IPs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subnet-monitor')
def api_subnet_monitor():
    """API for subnet monitoring with configurable CIDR"""
    try:
        # Get CIDR from query parameter, default to 24
        cidr = request.args.get('cidr', 24, type=int)
        
        # Validate CIDR range
        if cidr < 8 or cidr > 30:
            return jsonify({'error': 'CIDR must be between 8 and 30'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all IPs with their status and Service Domain info
        cursor.execute("""
            SELECT ip_address, status, subnet, vrf_vpn
            FROM ip_inventory 
            ORDER BY INET_ATON(ip_address)
        """)
        
        ips = cursor.fetchall()
        cursor.close()
        connection.close()
        
        if not ips:
            return jsonify({'subnets': [], 'cidr': cidr})
        
        # Group IPs by subnet based on the specified CIDR
        subnet_summary = {}
        
        for ip_data in ips:
            ip_str = ip_data['ip_address']
            status = ip_data['status']
            vrf_vpn = ip_data.get('vrf_vpn', 'default')
            
            try:
                # Create IP object
                ip_obj = ipaddress.IPv4Address(ip_str)
                
                # Calculate subnet based on the CIDR
                network = ipaddress.IPv4Network(f"{ip_str}/{cidr}", strict=False)
                subnet_str = str(network)
                
                # Initialize subnet if not exists
                if subnet_str not in subnet_summary:
                    # Calculate total addresses in subnet (exclude network and broadcast for /24 and larger)
                    total_addresses = 2 ** (32 - cidr)
                    if cidr < 31:
                        total_addresses -= 2  # Exclude network and broadcast
                    else:
                        total_addresses = 2 if cidr == 31 else 1  # Point-to-point or host route
                    
                    subnet_summary[subnet_str] = {
                        'subnet': subnet_str,
                        'network': str(network.network_address),
                        'cidr': cidr,
                        'total_addresses': total_addresses,
                        'used': 0,
                        'available': 0,
                        'reserved': 0,
                        'usage_percentage': 0,
                        'ips': [],
                        'vrf_vpns': set()  # Track unique Service Domains
                    }
                
                # Count by status
                if status == 'used':
                    subnet_summary[subnet_str]['used'] += 1
                elif status == 'available':
                    subnet_summary[subnet_str]['available'] += 1
                elif status == 'reserved':
                    subnet_summary[subnet_str]['reserved'] += 1
                
                # Add Service Domain to the set
                if vrf_vpn:
                    subnet_summary[subnet_str]['vrf_vpns'].add(vrf_vpn)
                
                # Add IP to the subnet
                subnet_summary[subnet_str]['ips'].append({
                    'ip': ip_str,
                    'status': status,
                    'vrf_vpn': vrf_vpn
                })
                
            except Exception as e:
                print(f"Error processing IP {ip_str}: {e}")
                continue
        
        # Calculate usage statistics and free addresses
        result_subnets = []
        for subnet_str, data in subnet_summary.items():
            used_count = data['used'] + data['reserved']  # Count reserved as used
            total_addresses = data['total_addresses']
            free_count = total_addresses - used_count
            
            # Ensure free count is not negative
            if free_count < 0:
                free_count = 0
            
            usage_percentage = (used_count / total_addresses * 100) if total_addresses > 0 else 0
            
            # Convert Service Domain set to sorted list
            vrf_list = sorted(list(data['vrf_vpns'])) if data['vrf_vpns'] else ['default']
            
            result_subnets.append({
                'subnet': subnet_str,
                'network': data['network'],
                'cidr': cidr,
                'total_addresses': total_addresses,
                'used': used_count,
                'free': free_count,
                'usage_percentage': round(usage_percentage, 2),
                'status_color': get_usage_color(usage_percentage),
                'vrf_vpns': vrf_list
            })
        
        # Sort subnets by network address
        result_subnets.sort(key=lambda x: ipaddress.IPv4Network(x['subnet']).network_address)
        
        return jsonify({
            'subnets': result_subnets,
            'cidr': cidr,
            'total_subnets': len(result_subnets)
        })
        
    except Error as e:
        print(f"❌ Error in subnet monitor: {e}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        print(f"❌ General error in subnet monitor: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subnets', methods=['GET'])
def api_get_subnets():
    """Get all subnets from database"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM subnets 
            ORDER BY subnet
        """)
        
        subnets = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return jsonify({'subnets': subnets})
        
    except Error as e:
        print(f"❌ Error getting subnets: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subnets', methods=['POST'])
def api_add_subnet():
    """Add a new subnet"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('subnet'):
            return jsonify({'error': 'Subnet is required'}), 400
            
        # Validate subnet format
        try:
            ipaddress.IPv4Network(data['subnet'], strict=False)
        except:
            return jsonify({'error': 'Invalid subnet format'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        
        # Check if subnet already exists
        cursor.execute("SELECT id FROM subnets WHERE subnet = %s", (data['subnet'],))
        if cursor.fetchone():
            return jsonify({'error': 'Subnet already exists'}), 400
        
        # Insert new subnet
        cursor.execute("""
            INSERT INTO subnets (
                subnet, description, section, vlan, device, nameservers,
                master_subnet, vrf, customer, location, mark_as_pool,
                mark_as_full, threshold_percentage, check_hosts_status,
                discover_new_hosts, resolve_dns_names, show_as_name, irr
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['subnet'],
            data.get('description', ''),
            data.get('section', ''),
            data.get('vlan', ''),
            data.get('device', ''),
            data.get('nameservers', ''),
            data.get('master_subnet', ''),
            data.get('vrf', ''),
            data.get('customer', ''),
            data.get('location', ''),
            data.get('mark_as_pool', False),
            data.get('mark_as_full', False),
            data.get('threshold_percentage', 80),
            data.get('check_hosts_status', False),
            data.get('discover_new_hosts', False),
            data.get('resolve_dns_names', False),
            data.get('show_as_name', False),
            data.get('irr', '')
        ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'message': 'Subnet added successfully'}), 201
        
    except Error as e:
        print(f"❌ Error adding subnet: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subnets/<int:subnet_id>', methods=['PUT'])
def api_update_subnet(subnet_id):
    """Update an existing subnet"""
    try:
        data = request.get_json()
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        
        # Check if subnet exists
        cursor.execute("SELECT id FROM subnets WHERE id = %s", (subnet_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Subnet not found'}), 404
        
        # Update subnet
        cursor.execute("""
            UPDATE subnets SET
                description = %s, section = %s, vlan = %s, device = %s,
                nameservers = %s, master_subnet = %s, vrf = %s, customer = %s,
                location = %s, mark_as_pool = %s, mark_as_full = %s,
                threshold_percentage = %s, check_hosts_status = %s,
                discover_new_hosts = %s, resolve_dns_names = %s,
                show_as_name = %s, irr = %s
            WHERE id = %s
        """, (
            data.get('description', ''),
            data.get('section', ''),
            data.get('vlan', ''),
            data.get('device', ''),
            data.get('nameservers', ''),
            data.get('master_subnet', ''),
            data.get('vrf', ''),
            data.get('customer', ''),
            data.get('location', ''),
            data.get('mark_as_pool', False),
            data.get('mark_as_full', False),
            data.get('threshold_percentage', 80),
            data.get('check_hosts_status', False),
            data.get('discover_new_hosts', False),
            data.get('resolve_dns_names', False),
            data.get('show_as_name', False),
            data.get('irr', ''),
            subnet_id
        ))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'message': 'Subnet updated successfully'})
        
    except Error as e:
        print(f"❌ Error updating subnet: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subnets/<int:subnet_id>', methods=['DELETE'])
def api_delete_subnet(subnet_id):
    """Delete a subnet"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        
        # Check if subnet exists
        cursor.execute("SELECT id FROM subnets WHERE id = %s", (subnet_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Subnet not found'}), 404
        
        # Delete subnet
        cursor.execute("DELETE FROM subnets WHERE id = %s", (subnet_id,))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({'message': 'Subnet deleted successfully'})
        
    except Error as e:
        print(f"❌ Error deleting subnet: {e}")
        return jsonify({'error': str(e)}), 500

# ================== AUTOMATED IP ALLOCATION API ==================
@app.route('/api/suggest-ips', methods=['POST'])
def api_suggest_ips():
    """API to suggest available IPs in a subnet"""
    try:
        data = request.get_json()
        
        # Validate required fields
        subnet = data.get('subnet', '').strip()
        count = data.get('count', 1)
        
        if not subnet:
            return jsonify({'error': 'Subnet is required'}), 400
            
        if count < 1 or count > 100:
            return jsonify({'error': 'Count must be between 1 and 100'}), 400
        
        # Validate subnet format
        try:
            network = ipaddress.ip_network(subnet, strict=False)
        except ValueError:
            return jsonify({'error': 'Invalid subnet format'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all used IPs in this subnet
        cursor.execute("""
            SELECT ip_address, status 
            FROM ip_inventory 
            WHERE subnet = %s
        """, (subnet,))
        
        used_ips_data = cursor.fetchall()
        used_ips = set(row['ip_address'] for row in used_ips_data)
        
        cursor.close()
        connection.close()
        
        # Find available IPs
        available_ips = []
        suggested_ips = []
        
        for ip in network.hosts():
            ip_str = str(ip)
            if ip_str not in used_ips:
                available_ips.append(ip_str)
                
        # Get the requested number of IPs
        suggested_ips = available_ips[:count]
        
        if len(suggested_ips) < count:
            return jsonify({
                'warning': f'Only {len(suggested_ips)} IPs available, but {count} requested',
                'suggested_ips': suggested_ips,
                'available_count': len(available_ips),
                'subnet': subnet
            })
        
        return jsonify({
            'success': True,
            'suggested_ips': suggested_ips,
            'available_count': len(available_ips),
            'subnet': subnet
        })
        
    except Exception as e:
        print(f"❌ Error suggesting IPs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk-reserve', methods=['POST'])
def api_bulk_reserve():
    """API to reserve multiple IPs at once"""
    try:
        data = request.get_json()
        
        # Validate required fields
        ip_list = data.get('ip_list', [])
        subnet = data.get('subnet', '')
        vrf_vpn = data.get('vrf_vpn', '')
        service = data.get('service', '')
        description = data.get('description', '')
        
        if not ip_list:
            return jsonify({'error': 'IP list is required'}), 400
            
        if not subnet:
            return jsonify({'error': 'Subnet is required'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor()
        
        reserved_ips = []
        failed_ips = []
        
        for ip in ip_list:
            try:
                # Validate IP format
                ipaddress.ip_address(ip)
                
                # Check if IP already exists
                cursor.execute("SELECT id FROM ip_inventory WHERE ip_address = %s", (ip,))
                if cursor.fetchone():
                    failed_ips.append({'ip': ip, 'reason': 'IP already exists'})
                    continue
                
                # Insert new reserved IP
                insert_query = """
                    INSERT INTO ip_inventory 
                    (ip_address, subnet, status, vrf_vpn, hostname, description)
                    VALUES (%s, %s, 'reserved', %s, %s, %s)
                """
                
                hostname = f"{service}-{ip.split('.')[-1]}" if service else ''
                full_description = f"Reserved for {service}: {description}" if service else description
                
                cursor.execute(insert_query, (ip, subnet, vrf_vpn, hostname, full_description))
                reserved_ips.append(ip)
                
            except ValueError:
                failed_ips.append({'ip': ip, 'reason': 'Invalid IP format'})
            except Exception as e:
                failed_ips.append({'ip': ip, 'reason': str(e)})
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'reserved_ips': reserved_ips,
            'failed_ips': failed_ips,
            'total_reserved': len(reserved_ips),
            'total_failed': len(failed_ips)
        })
        
    except Exception as e:
        print(f"❌ Error in bulk reserve: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/available-subnets')
def api_available_subnets():
    """API to get list of available subnets"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all subnets with usage statistics
        cursor.execute("""
            SELECT 
                subnet,
                COUNT(*) as total_used,
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available_count,
                SUM(CASE WHEN status = 'used' THEN 1 ELSE 0 END) as used_count,
                SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) as reserved_count
            FROM ip_inventory 
            WHERE subnet IS NOT NULL AND subnet != ''
            GROUP BY subnet
            ORDER BY subnet
        """)
        
        subnet_stats = cursor.fetchall()
        
        # Calculate subnet capacities
        subnets = []
        for stats in subnet_stats:
            subnet = stats['subnet']
            try:
                network = ipaddress.ip_network(subnet, strict=False)
                total_capacity = len(list(network.hosts()))
                used_in_db = stats['used_count'] + stats['reserved_count']
                available_ips = total_capacity - used_in_db
                
                subnets.append({
                    'subnet': subnet,
                    'total_capacity': total_capacity,
                    'used_count': stats['used_count'],
                    'reserved_count': stats['reserved_count'], 
                    'available_count': available_ips,
                    'utilization_percent': round((used_in_db / total_capacity * 100), 2) if total_capacity > 0 else 0
                })
            except:
                continue
        
        cursor.close()
        connection.close()
        
        return jsonify({'subnets': subnets})
        
    except Exception as e:
        print(f"❌ Error getting available subnets: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vrf-list')
def api_vrf_list():
    """API to get list of VRF/Service Domains"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all unique VRF/VPN values
        cursor.execute("""
            SELECT DISTINCT vrf_vpn as vrf_name, COUNT(*) as ip_count
            FROM ip_inventory 
            WHERE vrf_vpn IS NOT NULL AND vrf_vpn != ''
            GROUP BY vrf_vpn
            ORDER BY vrf_vpn
        """)
        
        vrfs = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return jsonify({'vrfs': vrfs})
        
    except Exception as e:
        print(f"❌ Error getting VRF list: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/smart-subnet-recommendations')
def api_smart_subnet_recommendations():
    """API to get smart subnet recommendations based on requirements"""
    try:
        # Get parameters
        required_ips = request.args.get('required_ips', 1, type=int)
        service_type = request.args.get('service_type', '')
        vrf_preference = request.args.get('vrf_preference', '')
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all subnets with detailed analysis
        cursor.execute("""
            SELECT 
                subnet,
                COUNT(*) as total_used,
                SUM(CASE WHEN status = 'used' THEN 1 ELSE 0 END) as used_count,
                SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) as reserved_count,
                GROUP_CONCAT(DISTINCT vrf_vpn) as vrfs,
                MAX(updated_at) as last_activity
            FROM ip_inventory 
            WHERE subnet IS NOT NULL AND subnet != ''
            GROUP BY subnet
            ORDER BY subnet
        """)
        
        subnet_stats = cursor.fetchall()
        cursor.close()
        connection.close()
        
        # Analyze and score subnets
        recommendations = []
        
        for stats in subnet_stats:
            subnet = stats['subnet']
            try:
                import ipaddress
                network = ipaddress.ip_network(subnet, strict=False)
                total_capacity = len(list(network.hosts()))
                used_in_db = stats['used_count'] + stats['reserved_count']
                available_ips = total_capacity - used_in_db
                
                if available_ips < required_ips:
                    continue  # Skip if not enough IPs
                
                # Calculate recommendation score
                score = calculate_subnet_score(
                    subnet, available_ips, total_capacity, used_in_db,
                    stats['vrfs'], service_type, vrf_preference, 
                    stats['last_activity'], required_ips
                )
                
                recommendations.append({
                    'subnet': subnet,
                    'total_capacity': total_capacity,
                    'used_count': stats['used_count'],
                    'reserved_count': stats['reserved_count'],
                    'available_count': available_ips,
                    'utilization_percent': round((used_in_db / total_capacity * 100), 2),
                    'recommendation_score': score['total_score'],
                    'score_breakdown': score['breakdown'],
                    'recommendation_reason': score['reason'],
                    'vrfs': stats['vrfs'],
                    'last_activity': stats['last_activity'].strftime('%Y-%m-%d') if stats['last_activity'] else 'Never',
                    'network_class': get_network_class(subnet),
                    'is_private': is_private_network(subnet)
                })
                
            except Exception as e:
                print(f"Error analyzing subnet {subnet}: {e}")
                continue
        
        # Sort by recommendation score (highest first)
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return jsonify({
            'recommendations': recommendations[:10],  # Top 10 recommendations
            'total_analyzed': len(subnet_stats),
            'meeting_requirements': len(recommendations),
            'requirements': {
                'required_ips': required_ips,
                'service_type': service_type,
                'vrf_preference': vrf_preference
            }
        })
        
    except Exception as e:
        print(f"❌ Error getting smart recommendations: {e}")
        return jsonify({'error': str(e)}), 500

def calculate_subnet_score(subnet, available_ips, total_capacity, used_ips, 
                          vrfs, service_type, vrf_preference, last_activity, required_ips):
    """Calculate recommendation score for a subnet"""
    
    score_breakdown = {}
    total_score = 0
    reasons = []
    
    # 1. Availability Score (40% weight)
    availability_ratio = available_ips / total_capacity
    if availability_ratio > 0.7:
        availability_score = 100
        reasons.append("High availability (>70%)")
    elif availability_ratio > 0.5:
        availability_score = 80
        reasons.append("Good availability (>50%)")
    elif availability_ratio > 0.3:
        availability_score = 60
        reasons.append("Moderate availability (>30%)")
    else:
        availability_score = 40
        reasons.append("Limited availability")
    
    score_breakdown['availability'] = availability_score
    total_score += availability_score * 0.4
    
    # 2. Capacity Efficiency Score (25% weight)
    if available_ips >= required_ips * 3:
        capacity_score = 100
        reasons.append("Excellent capacity margin")
    elif available_ips >= required_ips * 2:
        capacity_score = 80
        reasons.append("Good capacity margin")
    elif available_ips >= required_ips * 1.5:
        capacity_score = 60
        reasons.append("Adequate capacity margin")
    else:
        capacity_score = 40
        reasons.append("Minimal capacity margin")
    
    score_breakdown['capacity'] = capacity_score
    total_score += capacity_score * 0.25
    
    # 3. VRF Compatibility Score (20% weight)
    vrf_score = 50  # Default
    if vrf_preference and vrfs:
        if vrf_preference in vrfs:
            vrf_score = 100
            reasons.append("Perfect VRF match")
        else:
            vrf_score = 30
            reasons.append("Different VRF domain")
    elif not vrf_preference:
        vrf_score = 70
        reasons.append("No VRF preference")
    
    score_breakdown['vrf_compatibility'] = vrf_score
    total_score += vrf_score * 0.2
    
    # 4. Network Type Score (15% weight)
    network_score = 50
    if is_private_network(subnet):
        if service_type in ['web-server', 'application', 'database']:
            network_score = 90
            reasons.append("Private network suitable for internal services")
        else:
            network_score = 70
    else:
        if service_type in ['web-server', 'load-balancer']:
            network_score = 90
            reasons.append("Public network suitable for external services")
        else:
            network_score = 60
    
    score_breakdown['network_type'] = network_score
    total_score += network_score * 0.15
    
    return {
        'total_score': round(total_score, 1),
        'breakdown': score_breakdown,
        'reason': '; '.join(reasons[:3])  # Top 3 reasons
    }

def get_network_class(subnet):
    """Get network class (A, B, C) for subnet"""
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        first_octet = int(str(network.network_address).split('.')[0])
        
        if 1 <= first_octet <= 126:
            return 'Class A'
        elif 128 <= first_octet <= 191:
            return 'Class B'
        elif 192 <= first_octet <= 223:
            return 'Class C'
        else:
            return 'Special'
    except:
        return 'Unknown'

def is_private_network(subnet):
    """Check if subnet is in private IP range"""
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        return network.is_private
    except:
        return False

def get_usage_color(percentage):
    """Get color based on usage percentage"""
    if percentage < 50:
        return 'green'
    elif percentage < 80:
        return 'yellow' 
    else:
        return 'red'

@app.route('/subnet-monitor')
def subnet_monitor():
    """Subnet Monitor Dashboard"""
    return render_template('subnet_monitor.html')

@app.route('/ip-auto-allocation')
def ip_auto_allocation():
    """IP Auto Allocation - Smart IP Management"""
    return render_template('ip_auto_allocation.html')

@app.route('/api/ip-data')
def get_ip_data():
    """Get IP data by status for dashboard modals"""
    status = request.args.get('status', 'available')
    limit = int(request.args.get('limit', 100))
    format_type = request.args.get('format', 'json')
    
    try:
        cursor = mysql_connection.cursor(dictionary=True)
        
        # Define status conditions
        status_conditions = {
            'available': "hostname = ''",
            'used': "hostname != ''",
            'reserved': "ip_address LIKE '%reserved%' OR description LIKE '%reserved%'"
        }
        
        condition = status_conditions.get(status, "1=1")
        
        query = f"""
        SELECT ip_address, hostname, vrf_vpn, description,
               (SELECT subnet FROM subnets s WHERE INET_ATON(ip.ip_address) 
                BETWEEN INET_ATON(SUBSTRING_INDEX(s.subnet, '/', 1)) 
                AND INET_ATON(SUBSTRING_INDEX(s.subnet, '/', 1)) + POW(2, 32-SUBSTRING_INDEX(s.subnet, '/', -1)) - 1
                LIMIT 1) as subnet
        FROM ip_inventory ip
        WHERE {condition}
        ORDER BY INET_ATON(ip_address)
        LIMIT {limit}
        """
        
        cursor.execute(query)
        data = cursor.fetchall()
        
        if format_type == 'csv':
            # Return CSV format
            output = []
            output.append('IP Address,Hostname,VRF,Description,Subnet')
            for row in data:
                output.append(f"{row['ip_address']},{row['hostname'] or ''},{row['vrf_vpn'] or ''},{row['description'] or ''},{row['subnet'] or ''}")
            
            response = make_response('\n'.join(output))
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename={status}_ips.csv'
            return response
        
        return jsonify({'data': data, 'count': len(data)})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/subnets-overview')
def get_subnets_overview():
    """Get subnet overview for dashboard modal"""
    try:
        cursor = mysql_connection.cursor(dictionary=True)
        
        # Get subnet information with utilization
        query = """
        SELECT 
            s.subnet,
            s.description,
            s.vrf_vpn,
            POWER(2, 32 - SUBSTRING_INDEX(s.subnet, '/', -1)) - 2 as total_ips,
            COUNT(CASE WHEN ip.hostname != '' THEN 1 END) as used_ips,
            POWER(2, 32 - SUBSTRING_INDEX(s.subnet, '/', -1)) - 2 - COUNT(CASE WHEN ip.hostname != '' THEN 1 END) as available_ips,
            ROUND((COUNT(CASE WHEN ip.hostname != '' THEN 1 END) / (POWER(2, 32 - SUBSTRING_INDEX(s.subnet, '/', -1)) - 2)) * 100, 2) as utilization
        FROM subnets s
        LEFT JOIN ip_inventory ip ON (
            INET_ATON(ip.ip_address) BETWEEN 
            INET_ATON(SUBSTRING_INDEX(s.subnet, '/', 1)) + 1 AND 
            INET_ATON(SUBSTRING_INDEX(s.subnet, '/', 1)) + POWER(2, 32 - SUBSTRING_INDEX(s.subnet, '/', -1)) - 2
        )
        GROUP BY s.subnet, s.description, s.vrf_vpn
        ORDER BY utilization DESC
        """
        
        cursor.execute(query)
        subnets = cursor.fetchall()
        
        return jsonify({'subnets': subnets})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vrf-distribution')
def get_vrf_distribution():
    """Get VRF distribution data for charts"""
    try:
        cursor = mysql_connection.cursor(dictionary=True)
        
        query = """
        SELECT 
            vrf_vpn,
            COUNT(*) as count,
            COUNT(CASE WHEN hostname != '' THEN 1 END) as used_count,
            COUNT(CASE WHEN hostname = '' THEN 1 END) as available_count
        FROM ip_inventory 
        WHERE vrf_vpn IS NOT NULL AND vrf_vpn != ''
        GROUP BY vrf_vpn
        ORDER BY count DESC
        """
        
        cursor.execute(query)
        data = cursor.fetchall()
        
        return jsonify({'data': data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent-activity')
def get_recent_activity():
    """Get recent activity data"""
    try:
        cursor = mysql_connection.cursor(dictionary=True)
        
        # Simulate recent activity based on IP data
        query = """
        SELECT 
            ip_address,
            hostname,
            vrf_vpn,
            description,
            CASE 
                WHEN hostname != '' THEN 'Allocated'
                WHEN hostname = '' THEN 'Released'
                ELSE 'Updated'
            END as action,
            NOW() - INTERVAL FLOOR(RAND() * 168) HOUR as timestamp
        FROM ip_inventory 
        WHERE hostname != '' OR description LIKE '%recent%'
        ORDER BY timestamp DESC
        LIMIT 20
        """
        
        cursor.execute(query)
        activities = cursor.fetchall()
        
        # Convert timestamp to string for JSON serialization
        for activity in activities:
            activity['timestamp'] = activity['timestamp'].isoformat() if activity['timestamp'] else None
        
        return jsonify({'activities': activities})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Existing routes continue...
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Starting IPAM System - Clean Version")
    print("="*60)
    
    # Initialize database
    init_database()
    
    print("\n🌐 Server URLs:")
    print("   Main (IP Management): http://127.0.0.1:5005")
    print("   IP Management:        http://127.0.0.1:5005/ip-management")
    print("\n" + "="*60)
    print("✅ Server ready!")
    print("="*60)
    
    app.run(host='127.0.0.1', port=5005, debug=True)
