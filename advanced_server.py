"""
Advanced IPAM System
Complete IP Address Management with Advanced UI
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector
from mysql.connector import Error
import json
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
            
            # Create ip_inventory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_inventory (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ip_address VARCHAR(45) NOT NULL UNIQUE,
                    subnet VARCHAR(50),
                    status ENUM('used', 'available', 'reserved') DEFAULT 'available',
                    vrf_vpn VARCHAR(100),
                    hostname VARCHAR(255),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            connection.commit()
            cursor.close()
            connection.close()
            print("✅ Database initialized successfully")
            
    except Error as e:
        print(f"❌ Database initialization error: {e}")

def get_advanced_statistics():
    """Get advanced IP statistics with calculated available IPs"""
    try:
        connection = get_db_connection()
        if not connection:
            return {}
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all subnets and their used IPs
        cursor.execute("""
            SELECT 
                subnet,
                COUNT(*) as used_count,
                SUM(CASE WHEN status = 'used' THEN 1 ELSE 0 END) as actually_used,
                SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) as reserved,
                GROUP_CONCAT(DISTINCT vrf_vpn) as vrfs
            FROM ip_inventory 
            WHERE subnet IS NOT NULL AND subnet != ''
            GROUP BY subnet
        """)
        
        subnet_data = cursor.fetchall()
        
        total_subnet_ips = 0
        total_used_ips = 0
        total_reserved_ips = 0
        total_available_ips = 0
        
        public_available = 0
        private_available = 0
        
        vrf_stats = {}
        subnet_types = {
            'public': {'total': 0, 'used': 0, 'available': 0},
            'private': {'total': 0, 'used': 0, 'available': 0},
            'wan': {'total': 0, 'used': 0, 'available': 0},
            'global': {'total': 0, 'used': 0, 'available': 0}
        }
        
        for subnet in subnet_data:
            try:
                network = ipaddress.ip_network(subnet['subnet'], strict=False)
                subnet_size = network.num_addresses - 2  # Exclude network and broadcast
                
                if subnet_size <= 0:
                    continue
                    
                total_subnet_ips += subnet_size
                used_in_subnet = subnet['actually_used'] or 0
                reserved_in_subnet = subnet['reserved'] or 0
                available_in_subnet = subnet_size - used_in_subnet - reserved_in_subnet
                
                total_used_ips += used_in_subnet
                total_reserved_ips += reserved_in_subnet
                total_available_ips += available_in_subnet
                
                # Classify subnet type
                subnet_type = classify_subnet(str(network.network_address), subnet['subnet'])
                
                if subnet_type in subnet_types:
                    subnet_types[subnet_type]['total'] += subnet_size
                    subnet_types[subnet_type]['used'] += used_in_subnet
                    subnet_types[subnet_type]['available'] += available_in_subnet
                
                # VRF/VPN statistics
                if subnet['vrfs']:
                    for vrf in subnet['vrfs'].split(','):
                        vrf = vrf.strip()
                        if vrf and vrf != 'None':
                            if vrf not in vrf_stats:
                                vrf_stats[vrf] = {'total': 0, 'used': 0, 'available': 0}
                            vrf_stats[vrf]['total'] += subnet_size
                            vrf_stats[vrf]['used'] += used_in_subnet
                            vrf_stats[vrf]['available'] += available_in_subnet
                
                # Public/Private classification
                if network.is_private:
                    private_available += available_in_subnet
                else:
                    public_available += available_in_subnet
                    
            except Exception as e:
                print(f"Error processing subnet {subnet['subnet']}: {e}")
                continue
        
        # Get total unique subnets
        cursor.execute("SELECT COUNT(DISTINCT subnet) as count FROM ip_inventory WHERE subnet IS NOT NULL")
        subnet_result = cursor.fetchone()
        total_subnets = subnet_result['count'] if subnet_result else 0
        
        cursor.close()
        connection.close()
        
        return {
            'total_ips': total_subnet_ips,
            'used_ips': total_used_ips,
            'reserved_ips': total_reserved_ips,
            'available_ips': total_available_ips,
            'total_subnets': total_subnets,
            'public_available': public_available,
            'private_available': private_available,
            'subnet_types': subnet_types,
            'vrf_stats': vrf_stats,
            'utilization_percent': round((total_used_ips / total_subnet_ips * 100), 2) if total_subnet_ips > 0 else 0
        }
        
    except Error as e:
        print(f"❌ Error getting advanced statistics: {e}")
        return {}

def classify_subnet(ip_address, subnet):
    """Classify subnet type based on IP address and subnet"""
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        
        # WAN classification (common WAN ranges)
        wan_ranges = [
            '10.0.0.0/8',      # Private Class A (often used for WAN)
            '172.16.0.0/12',   # Private Class B
            '203.0.0.0/8',     # Public ranges often used for WAN
            '202.0.0.0/8',
            '61.0.0.0/8'
        ]
        
        for wan_range in wan_ranges:
            if network.overlaps(ipaddress.ip_network(wan_range)):
                # Check if it's likely WAN based on subnet size or naming
                if '/30' in subnet or '/31' in subnet or network.num_addresses <= 4:
                    return 'wan'
        
        # Public vs Private
        if network.is_private:
            return 'private'
        else:
            return 'public'
            
    except:
        return 'global'

def get_statistics():
    """Get IP statistics"""
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
        
        # Total subnets
        cursor.execute("SELECT COUNT(DISTINCT subnet) as count FROM ip_inventory WHERE subnet IS NOT NULL")
        subnet_result = cursor.fetchone()
        stats['total_subnets'] = subnet_result['count'] if subnet_result else 0
        
        cursor.close()
        connection.close()
        
        return stats
        
    except Error as e:
        print(f"❌ Error getting statistics: {e}")
        return {}

# Routes
@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template('advanced_ipam.html')

@app.route('/ip-management')
def ip_management():
    """IP Management page"""
    return render_template('advanced_ipam.html')

@app.route('/api/ip-data')
def api_ip_data():
    """API to get IP data with pagination and search"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '').strip()
        
        offset = (page - 1) * limit
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Build WHERE conditions
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
        cursor.execute(count_query, params[:-2] if params else [])
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
    """API to get statistics with calculated available IPs"""
    stats = get_advanced_statistics()
    return jsonify(stats)

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

@app.route('/api/subnet-overview')
def api_subnet_overview():
    """API: Get subnet overview with usage statistics"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all subnets with their usage
        cursor.execute("""
            SELECT 
                subnet,
                COUNT(*) as total_ips,
                SUM(CASE WHEN status = 'used' THEN 1 ELSE 0 END) as used_ips,
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available_ips,
                SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) as reserved_ips
            FROM ip_inventory 
            WHERE subnet IS NOT NULL AND subnet != ''
            GROUP BY subnet
            ORDER BY subnet
        """)
        
        subnets = cursor.fetchall()
        
        # Calculate usage percentage and add network info
        for subnet in subnets:
            try:
                network = ipaddress.ip_network(subnet['subnet'], strict=False)
                actual_subnet_size = network.num_addresses - 2  # Exclude network and broadcast
                
                # Calculate real usage based on subnet size
                used_count = subnet['used_ips'] or 0
                reserved_count = subnet['reserved_ips'] or 0
                actual_available = actual_subnet_size - used_count - reserved_count
                
                subnet['network_size'] = actual_subnet_size
                subnet['actual_available'] = actual_available
                subnet['is_private'] = network.is_private
                subnet['subnet_type'] = classify_subnet(str(network.network_address), subnet['subnet'])
                
                if actual_subnet_size > 0:
                    subnet['usage_percent'] = round(((used_count + reserved_count) / actual_subnet_size) * 100, 1)
                else:
                    subnet['usage_percent'] = 0
                    
            except:
                subnet['network_size'] = subnet['total_ips']
                subnet['actual_available'] = 0
                subnet['is_private'] = True
                subnet['subnet_type'] = 'unknown'
                subnet['usage_percent'] = 0
        
        cursor.close()
        connection.close()
        
        return jsonify(subnets)
        
    except Error as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/advanced-monitoring')
def api_advanced_monitoring():
    """API: Advanced monitoring for different IP categories"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = connection.cursor(dictionary=True)
        
        # Get all subnets with detailed info
        cursor.execute("""
            SELECT 
                subnet,
                vrf_vpn,
                status,
                COUNT(*) as count,
                GROUP_CONCAT(ip_address) as ip_list
            FROM ip_inventory 
            WHERE subnet IS NOT NULL AND subnet != ''
            GROUP BY subnet, vrf_vpn, status
            ORDER BY subnet, vrf_vpn
        """)
        
        raw_data = cursor.fetchall()
        
        # Process monitoring data
        monitoring_data = {
            'ip_public': {'total': 0, 'used': 0, 'available': 0, 'subnets': []},
            'ip_private': {'total': 0, 'used': 0, 'available': 0, 'subnets': []},
            'ip_wan': {'total': 0, 'used': 0, 'available': 0, 'subnets': []},
            'ip_global': {'total': 0, 'used': 0, 'available': 0, 'subnets': []},
            'vrf_vpn': {}
        }
        
        # Group by subnet first
        subnet_groups = {}
        for row in raw_data:
            subnet = row['subnet']
            if subnet not in subnet_groups:
                subnet_groups[subnet] = {'used': 0, 'available': 0, 'reserved': 0, 'vrfs': set()}
            
            if row['vrf_vpn']:
                subnet_groups[subnet]['vrfs'].add(row['vrf_vpn'])
            
            if row['status'] == 'used':
                subnet_groups[subnet]['used'] += row['count']
            elif row['status'] == 'available':
                subnet_groups[subnet]['available'] += row['count']
            elif row['status'] == 'reserved':
                subnet_groups[subnet]['reserved'] += row['count']
        
        # Process each subnet
        for subnet, data in subnet_groups.items():
            try:
                network = ipaddress.ip_network(subnet, strict=False)
                actual_size = network.num_addresses - 2
                
                if actual_size <= 0:
                    continue
                
                # Calculate real available IPs
                used_count = data['used']
                reserved_count = data['reserved']
                real_available = actual_size - used_count - reserved_count
                
                subnet_info = {
                    'subnet': subnet,
                    'total': actual_size,
                    'used': used_count,
                    'available': real_available,
                    'reserved': reserved_count,
                    'utilization': round((used_count / actual_size * 100), 2) if actual_size > 0 else 0
                }
                
                # Classify subnet type
                subnet_type = classify_subnet(str(network.network_address), subnet)
                
                if subnet_type == 'public':
                    monitoring_data['ip_public']['total'] += actual_size
                    monitoring_data['ip_public']['used'] += used_count
                    monitoring_data['ip_public']['available'] += real_available
                    monitoring_data['ip_public']['subnets'].append(subnet_info)
                elif subnet_type == 'private':
                    monitoring_data['ip_private']['total'] += actual_size
                    monitoring_data['ip_private']['used'] += used_count
                    monitoring_data['ip_private']['available'] += real_available
                    monitoring_data['ip_private']['subnets'].append(subnet_info)
                elif subnet_type == 'wan':
                    monitoring_data['ip_wan']['total'] += actual_size
                    monitoring_data['ip_wan']['used'] += used_count
                    monitoring_data['ip_wan']['available'] += real_available
                    monitoring_data['ip_wan']['subnets'].append(subnet_info)
                else:
                    monitoring_data['ip_global']['total'] += actual_size
                    monitoring_data['ip_global']['used'] += used_count
                    monitoring_data['ip_global']['available'] += real_available
                    monitoring_data['ip_global']['subnets'].append(subnet_info)
                
                # Process VRF/VPN data
                for vrf in data['vrfs']:
                    if vrf and vrf.strip() and vrf != 'None':
                        vrf = vrf.strip()
                        if vrf not in monitoring_data['vrf_vpn']:
                            monitoring_data['vrf_vpn'][vrf] = {
                                'total': 0, 'used': 0, 'available': 0, 'subnets': []
                            }
                        
                        monitoring_data['vrf_vpn'][vrf]['total'] += actual_size
                        monitoring_data['vrf_vpn'][vrf]['used'] += used_count
                        monitoring_data['vrf_vpn'][vrf]['available'] += real_available
                        monitoring_data['vrf_vpn'][vrf]['subnets'].append(subnet_info.copy())
                
            except Exception as e:
                print(f"Error processing subnet {subnet}: {e}")
                continue
        
        cursor.close()
        connection.close()
        
        return jsonify(monitoring_data)
        
    except Error as e:
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
                return jsonify({'error': f'Field {field} is required'}), 400
        
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

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Starting Advanced IPAM System")
    print("="*60)
    
    # Initialize database
    init_database()
    
    print("\n🌐 Server URLs:")
    print("   Dashboard:            http://127.0.0.1:5005")
    print("   IP Management:        http://127.0.0.1:5005/ip-management")
    print("\n" + "="*60)
    print("✅ Advanced IPAM Server ready!")
    print("="*60)
    
    app.run(host='127.0.0.1', port=5005, debug=True)
