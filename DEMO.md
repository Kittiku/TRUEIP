# IPAM System - Installation & Demo Guide

## 🚀 Quick Setup

### 1. Clone Repository
```bash
git clone https://github.com/Kittiku/IPAM.git
cd IPAM
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup MySQL Database
- Install MySQL Server
- Create user: `root` with password: `9371`
- Or modify credentials in `mysql_manager.py`

### 4. Add Data File
- Place your `datalake.Inventory.port.csv` file in the project root
- This file contains network port interface data

### 5. Run Application
```bash
python main_server.py
# OR for Windows
start_ipam.bat
```

### 6. Access System
- **Main Dashboard**: http://127.0.0.1:5005
- **IP Management**: http://127.0.0.1:5005/ip-management

## 📊 Sample Data Structure

Your `datalake.Inventory.port.csv` should contain columns like:
```
id, host_id, host_name, ifName, ifIP, ifOperStatus, vendor, domain, etc.
```

## 🔧 Configuration

### Database Settings
Edit `mysql_manager.py` to change database credentials:
```python
def __init__(self, host='localhost', user='root', password='9371', database='ipam_db'):
```

### Server Settings
Edit `main_server.py` to change server port:
```python
app.run(debug=True, host='127.0.0.1', port=5005)
```

## 📈 Features Demonstrated

1. **Real-time Dashboard**
   - Network device statistics
   - Active/inactive device monitoring
   - Vendor distribution charts

2. **IP Address Management**
   - IP conflict detection
   - Subnet analysis
   - Port interface monitoring

3. **Network Tree Structure**
   - Hierarchical device organization
   - Domain-based categorization
   - Performance optimized queries

## 🛠️ Troubleshooting

### MySQL Connection Issues
1. Ensure MySQL server is running
2. Check username/password
3. Verify database permissions

### Data Import Issues
1. Check CSV file format
2. Ensure file path is correct
3. Verify column names match expected format

### Performance Issues
1. System handles 400K+ records efficiently
2. Uses MySQL indexing and caching
3. Automatic data pagination

## 📞 Support

For technical support or questions about the IPAM system, refer to the main README.md or contact the development team.
