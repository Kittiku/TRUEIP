# IPAM - IP Address Management System

A simple and clean IP Address Management System built with Flask and MySQL.

## Features

- ✅ **IP Address Management**: Add, edit, delete, and search IP addresses
- ✅ **Status Tracking**: Track IP status (Used, Available, Reserved)
- ✅ **Subnet Management**: Organize IPs by subnets
- ✅ **Search & Filter**: Search by IP, hostname, or description
- ✅ **Statistics Dashboard**: Real-time statistics and reporting
- ✅ **Clean UI**: Modern responsive design with Tailwind CSS

## Screenshots

### Main Dashboard
![Dashboard](https://via.placeholder.com/800x400/4F46E5/FFFFFF?text=IP+Management+Dashboard)

## Installation

### Prerequisites
- Python 3.8+
- MySQL Server
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Kittiku/IPAM.git
   cd IPAM
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Database**
   - Install MySQL Server
   - Update database credentials in `main_server.py`:
   ```python
   DB_CONFIG = {
       'host': 'localhost',
       'user': 'root',
       'password': 'your_password',
       'database': 'ipam_db'
   }
   ```

4. **Create sample data (optional)**
   ```bash
   python create_sample_data.py
   ```

5. **Start the server**
   ```bash
   python main_server.py
   ```
   
   Or use the batch file on Windows:
   ```cmd
   start_ipam.bat
   ```

6. **Access the application**
   - Open browser: http://127.0.0.1:5005
   - Main page redirects to IP Management

## Usage

### Adding IP Addresses
1. Click "Add IP" button
2. Fill in required fields:
   - IP Address (required)
   - Subnet (required)
   - Status (required)
3. Optional fields:
   - VRF/VPN
   - Hostname
   - Description
4. Click "Save"

### Searching and Filtering
- **Search**: Type IP address, hostname, or description in search box
- **Filter by Status**: Use dropdown to filter by Used/Available/Reserved
- **Clear Filters**: Click "Clear" button to reset

### Editing IP Addresses
1. Click "Edit" button in the Actions column
2. Modify fields as needed
3. Click "Save"

### Deleting IP Addresses
1. Click "Delete" button in the Actions column
2. Confirm deletion in popup

## API Endpoints

### Get IP Data
```http
GET /api/ip-data?page=1&limit=50&search=&status=
```

### Add IP Address
```http
POST /api/add-ip
Content-Type: application/json

{
  "ip_address": "192.168.1.10",
  "subnet": "192.168.1.0/24",
  "status": "used",
  "vrf_vpn": "VRF-CORE",
  "hostname": "server01.example.com",
  "description": "Production server"
}
```

### Update IP Address
```http
PUT /api/update-ip/{id}
Content-Type: application/json

{
  "status": "available",
  "description": "Updated description"
}
```

### Delete IP Address
```http
DELETE /api/delete-ip/{id}
```

### Get Statistics
```http
GET /api/statistics
```

## Database Schema

### ip_inventory Table
| Column | Type | Description |
|--------|------|-------------|
| id | INT AUTO_INCREMENT | Primary key |
| ip_address | VARCHAR(15) | IP address (unique) |
| subnet | VARCHAR(18) | Subnet CIDR |
| status | ENUM | used/available/reserved |
| vrf_vpn | VARCHAR(50) | VRF or VPN name |
| hostname | VARCHAR(100) | Hostname |
| description | TEXT | Description |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update time |

## File Structure

```
IPAM/
├── main_server.py              # Main Flask application
├── create_sample_data.py       # Sample data generator
├── start_ipam.bat             # Windows startup script
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── templates/
    └── ip_management.html     # Main template
```

## Development

### Adding New Features
1. Update the database schema if needed
2. Add new API endpoints in `main_server.py`
3. Update the frontend in `templates/ip_management.html`
4. Test thoroughly

### Database Migration
The application automatically creates the database and tables on first run.

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check MySQL server is running
   - Verify credentials in `main_server.py`
   - Ensure database user has proper permissions

2. **Port Already in Use**
   - Change port in `main_server.py`: `app.run(port=5006)`
   - Or stop other applications using port 5005

3. **Template Not Found**
   - Ensure `templates/ip_management.html` exists
   - Check file permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Contact: [Your Email]

## Changelog

### v2.0.0 (Clean Version)
- Simplified to single IP Management page
- Removed complex SPA functionality
- Clean and focused UI
- Better performance
- Easier maintenance

### v1.0.0 (Original)
- Multi-page SPA application
- Complex dashboard with charts
- Multiple management interfaces
