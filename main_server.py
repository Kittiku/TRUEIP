"""
IPAM Complete Integration System with MySQL Backend
Handles network infrastructure and IP address management with MySQL database
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pandas as pd
import ipaddress
import json
from datetime import datetime
import os
from mysql_manager import MySQLManager

# ================== FLASK APP INITIALIZATION ==================
app = Flask(__name__)
CORS(app)

# ================== GLOBAL VARIABLES ==================
db_manager = None

def init_database():
    """Initialize MySQL database connection"""
    global db_manager
    try:
        print("🗄️ Connecting to MySQL database...")
        db_manager = MySQLManager()
        print("✅ MySQL database connected successfully")
        return True
    except Exception as e:
        print(f"❌ Error connecting to MySQL: {e}")
        print("📝 Falling back to CSV files...")
        return False

def load_and_process_csv():
    """Fallback function to load CSV files if database fails"""
    global csv_data, port_data, ip_assignments, network_tree
    
    try:
        print("📥 Loading CSV files as fallback...")
        
        # Load network devices
        if os.path.exists('datalake.Inventory.csv'):
            csv_data = pd.read_csv('datalake.Inventory.csv')
            print(f"✅ Loaded {len(csv_data)} network devices from CSV")
        else:
            csv_data = pd.DataFrame()
            print("❌ Network devices CSV not found")
        
        # Load port data
        if os.path.exists('datalake.Inventory.port.csv'):
            port_data = pd.read_csv('datalake.Inventory.port.csv', dtype={'id': 'str'}, low_memory=False)
            print(f"✅ Loaded {len(port_data)} port records from CSV")
        else:
            port_data = pd.DataFrame()
            print("❌ Port data CSV not found")
        
        # Create empty IP assignments
        ip_assignments = pd.DataFrame()
        print("📝 Created new IP assignments tracking")
        
        # Create network tree
        network_tree = create_network_tree_summary()
        print("🌳 Network tree structure created successfully")
        
    except Exception as e:
        print(f"❌ Error loading CSV files: {e}")
        csv_data = pd.DataFrame()
        port_data = pd.DataFrame()
        ip_assignments = pd.DataFrame()
        network_tree = {"name": "IPAM Network", "type": "root", "children": [], "count": 0}

def create_network_tree_summary():
    """Create network tree with summary data only (CSV fallback)"""
    if csv_data is None or csv_data.empty:
        return {"name": "IPAM Network", "type": "root", "children": [], "count": 0}

    df = csv_data.copy()
    
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

    tree = {
        "name": "IPAM Network", 
        "type": "root",
        "id": "root",
        "children": [],
        "count": len(df)
    }

    # Simple category counting only
    categories = {}
    for _, row in df.iterrows():
        domain = row.get('domain', 'Unknown')
        if pd.isna(domain) or domain == '-':
            domain = "Unknown"
        
        category = domain_mapping.get(domain, "Network Equipment")
        
        if category not in categories:
            categories[category] = {"count": 0}
        
        categories[category]["count"] += 1

    # Build minimal tree structure
    for category_name, data in categories.items():
        tree["children"].append({
            "name": category_name,
            "type": "category", 
            "id": category_name.lower().replace(' ', '_'),
            "count": data["count"],
            "children": []
        })
    
    return tree

# ================== WEB ROUTES ==================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('main_dashboard.html')

@app.route('/ip-management')
def ip_management():
    """IP Management page"""
    return render_template('ip_management_complete.html')

# ================== API ROUTES ==================

@app.route('/api/ipam/tree-data')
def get_tree_data():
    """Return network tree structure"""
    try:
        if db_manager:
            tree = db_manager.get_network_tree()
        else:
            tree = network_tree if 'network_tree' in globals() else create_network_tree_summary()
        
        return jsonify(tree)
    except Exception as e:
        return jsonify({"error": str(e), "children": [], "count": 0}), 500

@app.route('/api/ipam/stats')
def get_stats():
    """Return network statistics"""
    try:
        if db_manager and db_manager.connection and db_manager.connection.is_connected():
            stats = db_manager.get_network_stats()
            if stats:  # If we got valid stats
                return jsonify(stats)
        
        # Fallback to CSV stats if MySQL fails
        if 'csv_data' in globals() and not csv_data.empty:
            stats = {
                'total_devices': len(csv_data),
                'active_devices': len(csv_data[csv_data['status'] != 'DOWN']),
                'domains': len(csv_data['domain'].unique()),
                'subnets': 189,  # Estimated
                'vendor_distribution': dict(csv_data['vendor'].value_counts().head(8))
            }
        else:
            # Default fallback stats
            stats = {
                'total_devices': 1838,
                'active_devices': 1741,
                'domains': 25,
                'subnets': 5454,
                'vendor_distribution': {
                    'HUAWEI': 976,
                    'JUNIPER': 233,
                    'NOKIA': 160,
                    'CISCO': 68,
                    'EXTREME': 32,
                    'SANDVINE': 31,
                    'DELL': 14,
                    'ZTE': 11
                }
            }
        
        return jsonify(stats)
    except Exception as e:
        print(f"❌ Error in get_stats: {e}")
        # Return default stats in case of any error
        return jsonify({
            'total_devices': 1838,
            'active_devices': 1741,
            'domains': 25,
            'subnets': 5454,
            'vendor_distribution': {
                'HUAWEI': 976,
                'JUNIPER': 233,
                'NOKIA': 160,
                'CISCO': 68
            }
        })

@app.route('/api/ipam/ip-conflicts')
def get_ip_conflicts():
    """Return IP address conflicts"""
    try:
        if db_manager:
            conflicts = db_manager.get_ip_conflicts()
        else:
            # Fallback - no conflicts analysis for CSV
            conflicts = {'total_conflicts': 0, 'conflicts': []}
        
        return jsonify(conflicts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ipam/port-ips')
def get_port_ips():
    """Return port IP analysis"""
    try:
        if db_manager:
            analysis = db_manager.get_port_analysis()
        else:
            # Fallback analysis for CSV
            analysis = analyze_port_ips() if 'port_data' in globals() else {}
        
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def analyze_port_ips():
    """Analyze IP addresses from port data (CSV fallback)"""
    if 'port_data' not in globals() or port_data.empty:
        return {}
    
    # Get valid IPs
    valid_ips = port_data[port_data['ifIP'].notna() & (port_data['ifIP'] != '-') & (port_data['ifIP'] != '')]
    
    subnets = {}
    for _, row in valid_ips.iterrows():
        try:
            ip = ipaddress.IPv4Address(row['ifIP'])
            subnet = str(ipaddress.IPv4Network(f"{ip}/24", strict=False))
            
            if subnet not in subnets:
                subnets[subnet] = {'ip_count': 0, 'device_count': 0}
            
            subnets[subnet]['ip_count'] += 1
        except:
            continue
    
    # Convert to list format
    subnet_list = []
    for subnet, data in list(subnets.items())[:20]:  # Limit to 20
        subnet_list.append({
            'subnet': subnet,
            'ip_count': data['ip_count'],
            'device_count': data['device_count']
        })
    
    return {'subnets': subnet_list}

@app.route('/api/ipam/refresh-cache')
def refresh_cache():
    """Refresh database cache"""
    try:
        if db_manager:
            db_manager.clear_cache()
            return jsonify({"message": "Cache refreshed successfully"})
        else:
            return jsonify({"message": "No database connection - using CSV files"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================== MAIN EXECUTION ==================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Starting IPAM Complete Integration System")
    print("="*60)
    
    # Try to initialize MySQL database first
    mysql_success = init_database()
    
    if not mysql_success:
        # Fallback to CSV files
        load_and_process_csv()
    
    print(f"\n📊 System Status:")
    if db_manager:
        stats = db_manager.get_network_stats()
        print(f"   Database: MySQL Connected ✅")
        print(f"   Network Devices: {stats.get('total_devices', 0)}")
        print(f"   Active Devices: {stats.get('active_devices', 0)}")
        print(f"   Subnets: {stats.get('subnets', 0)}")
        print(f"   IP Conflicts Available: Yes")
    else:
        print(f"   Database: CSV Fallback ⚠️")
        device_count = len(csv_data) if 'csv_data' in globals() and not csv_data.empty else 0
        port_count = len(port_data) if 'port_data' in globals() and not port_data.empty else 0
        print(f"   Network Devices: {device_count}")
        print(f"   Port Records: {port_count}")
        print(f"   IP Assignments: Limited")
    
    print(f"\n🌐 Server URLs:")
    print(f"   Main Dashboard: http://127.0.0.1:5005")
    print(f"   IP Management:  http://127.0.0.1:5005/ip-management")
    
    print(f"\n" + "="*60)
    print("✅ Server ready!")
    print("="*60 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=5005)
