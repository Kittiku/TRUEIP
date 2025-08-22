# 🗺️ IPAM System - URL Navigation Guide

## 📍 **หน้าหลัก (Homepage)**
```
http://127.0.0.1:5005/
```
- **Description**: Network Sections Dashboard (Modern UI)
- **Features**: Overview ของ sections ทั้งหมด, statistics, section management
- **Template**: `network_dashboard.html`

---

## 🔗 **Main Navigation URLs**

### 1. **IP Management (Global)**
```
http://127.0.0.1:5005/ip-management
```
- **Description**: Global IP address management
- **Template**: `ip_management_clean.html`

### 2. **Subnet Manager**
```
http://127.0.0.1:5005/subnet-manager
```
- **Description**: Fast subnet management interface
- **Template**: `subnet_manager_fast.html`

### 3. **VRF Monitoring**
```
http://127.0.0.1:5005/vrf-monitoring
```
- **Description**: VRF monitoring dashboard
- **Template**: `subnet_monitor.html`

---

## 🛠️ **Advanced Tools**

### 4. **IP Auto Allocation**
```
http://127.0.0.1:5005/ip-auto-allocation
```
- **Description**: Smart IP allocation tools
- **Template**: `ip_auto_allocation.html`

### 5. **CSV Import**
```
http://127.0.0.1:5005/csv-import
```
- **Description**: Bulk data import functionality
- **Template**: `csv_import.html`

---

## 📂 **Section-Specific URLs**

### Section Dashboard
```
http://127.0.0.1:5005/section/{id}/dashboard
```
- **Example**: `http://127.0.0.1:5005/section/7/dashboard`
- **Description**: Individual section management dashboard

### Section IP Management
```
http://127.0.0.1:5005/section/{id}/ip-management
```
- **Example**: `http://127.0.0.1:5005/section/7/ip-management`

### Section Subnet Management
```
http://127.0.0.1:5005/section/{id}/subnet-management
```

### Section VRF Monitoring
```
http://127.0.0.1:5005/section/{id}/vrf-monitoring
```

### Section CSV Import
```
http://127.0.0.1:5005/section/{id}/csv-import
```

### Section IP Auto Allocation
```
http://127.0.0.1:5005/section/{id}/ip-auto-allocation
```

---

## 🔄 **Legacy/Alternative URLs**

### Legacy Network Sections (Bootstrap UI)
```
http://127.0.0.1:5005/network-sections
```
- **Description**: Old network sections interface
- **Template**: `network_sections.html`

### Classic IP Management
```
http://127.0.0.1:5005/ip-management-classic
```
- **Description**: Alternative IP management interface

---

## 🎯 **Quick Access Summary**

| **Function** | **URL** | **Type** |
|--------------|---------|----------|
| **🏠 Home** | `/` | Main Dashboard |
| **🌐 Global IP** | `/ip-management` | Global Tools |
| **🔗 Subnets** | `/subnet-manager` | Global Tools |
| **📊 VRF Monitor** | `/vrf-monitoring` | Global Tools |
| **🤖 Auto IP** | `/ip-auto-allocation` | Advanced |
| **📤 CSV Import** | `/csv-import` | Advanced |
| **📁 Section 7** | `/section/7/dashboard` | Section-Specific |

---

## 🎨 **UI Differences**

- **Modern UI** (Tailwind): `/` (Homepage)
- **Bootstrap UI**: `/network-sections` (Legacy)
- **Clean UI**: `/ip-management` (Global)

---

## 🚀 **Recommended Navigation Flow**

1. **Start**: http://127.0.0.1:5005/ (Homepage)
2. **Browse Sections**: Click on section cards
3. **Manage Section**: `/section/{id}/dashboard`
4. **Global Tools**: Use sidebar navigation
5. **Advanced Features**: CSV import, Auto allocation

---

## ⚡ **Quick Tips**

- **Sidebar Navigation**: ใช้ sidebar เพื่อเปลี่ยนหน้า
- **Section Cards**: คลิกที่การ์ด section เพื่อเข้าไปจัดการ
- **Breadcrumbs**: ใช้ breadcrumb navigation ในหน้า section
- **Back to Sections**: ปุ่ม "Back to Sections" ในหน้า section
