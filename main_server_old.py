"""
IPAM System - Clean Version
Simple IP Address Management System
Only IP Management functionality
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
    """Redirect to IP Management"""
    return redirect(url_for('ip_management'))

@app.route('/ip-management')
def ip_management():
    """Main IP Management page"""
    return render_template('ip_management.html')

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
    """API to get statistics"""
    stats = get_statistics()
    return jsonify(stats)

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
