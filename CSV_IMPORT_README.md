# 📁 CSV Import System - User Guide

## 🚀 Overview
ระบบ CSV Import สำหรับ IPAM ช่วยให้คุณสามารถนำเข้าข้อมูล IP addresses และ subnets จากไฟล์ CSV ได้อย่างง่ายดาย พร้อมการจัดการ duplicate data แบบอัจฉริยะ

## 📋 Features

### ✅ **การนำเข้าข้อมูล**
- Import IP Inventory (IP addresses, hostnames, VRF, descriptions)
- Import Subnets (subnet configurations, VLANs, devices)
- รองรับไฟล์ CSV ขนาดใหญ่ (สูงสุด 16MB)

### 🔍 **การจัดการ Duplicates**
- **Ask Mode** (แนะนำ): แสดง popup ให้เลือกกรณีพบข้อมูลซ้ำ
- **Keep Old**: เก็บข้อมูลเก่าทั้งหมด ข้อมูลใหม่จะถูกข้าม
- **Use New**: ใช้ข้อมูลใหม่ทับข้อมูลเก่าทั้งหมด

### 📊 **การตรวจสอบข้อมูล**
- Validation IP addresses และ subnet formats
- แสดงสถิติการ import แบบละเอียด
- Log แจ้งเตือนข้อผิดพลาด

## 📝 CSV File Format

### **IP Inventory CSV Format**
```csv
ip_address,subnet,hostname,vrf_vpn,description,status
192.168.1.1,192.168.1.0/24,gateway-router,CORP-VRF,Main gateway,used
192.168.1.10,192.168.1.0/24,web-server-01,CORP-VRF,Web server,used
192.168.1.50,192.168.1.0/24,,CORP-VRF,Reserved for future,reserved
192.168.1.100,192.168.1.0/24,,CORP-VRF,,available
```

**Required Fields:**
- `ip_address` (required) - ที่อยู่ IP ในรูปแบบ x.x.x.x
- `subnet` (optional) - Subnet ในรูปแบบ CIDR
- `hostname` (optional) - ชื่อ host/device
- `vrf_vpn` (optional) - VRF/VPN domain
- `description` (optional) - คำอธิบาย
- `status` (optional) - สถานะ: used, available, reserved

### **Subnets CSV Format**
```csv
subnet,description,section,vlan,device,vrf,customer,location,nameservers,threshold_percentage
192.168.1.0/24,Corporate LAN,CORPORATE,VLAN100,Core-Switch-01,CORP-VRF,Internal IT,Building A,"8.8.8.8,8.8.4.4",80
10.0.1.0/24,Management Network,MANAGEMENT,VLAN10,Mgmt-Switch-01,MGMT-VRF,Network Ops,Server Room,"10.0.1.1",75
```

**Required Fields:**
- `subnet` (required) - Subnet ในรูปแบบ CIDR (เช่น 192.168.1.0/24)
- `description` (optional) - คำอธิบาย subnet
- `section` (optional) - หมวดหมู่/กลุ่ม
- `vlan` (optional) - VLAN ID
- `device` (optional) - อุปกรณ์เครือข่าย
- `vrf` (optional) - VRF domain
- `customer` (optional) - ลูกค้า/แผนก
- `location` (optional) - สถานที่
- `nameservers` (optional) - DNS servers (คั่นด้วย comma)
- `threshold_percentage` (optional) - เปอร์เซ็นต์การแจ้งเตือน (ค่าเริ่มต้น 80)

## 🎯 How to Use

### **Step 1: Prepare CSV File**
1. ดาวน์โหลดไฟล์ตัวอย่างจากระบบ
2. แก้ไขข้อมูลตามต้องการ
3. บันทึกเป็นไฟล์ CSV (UTF-8 encoding)

### **Step 2: Import Process**
1. เข้าหน้า CSV Import
2. เลือกประเภทข้อมูล (IP Inventory หรือ Subnets)
3. เลือกกลยุทธ์การจัดการ duplicates
4. อัปโหลดไฟล์ CSV
5. ตรวจสอบผลลัพธ์

### **Step 3: Handle Conflicts (if any)**
1. ระบบจะแสดง popup กรณีพบข้อมูลซ้ำ
2. เปรียบเทียบข้อมูลเก่าและใหม่
3. เลือก "Keep existing" หรือ "Use new" สำหรับแต่ละรายการ
4. กดปุ่ม "Apply Resolutions"

## ⚠️ Important Notes

### **File Requirements:**
- ไฟล์ต้องเป็น CSV format เท่านั้น
- ขนาดไฟล์ไม่เกิน 16MB
- Encoding: UTF-8 (แนะนำ)
- ใช้ comma (,) เป็น delimiter

### **Data Validation:**
- IP addresses จะถูกตรวจสอบรูปแบบ
- Subnet CIDR จะถูกตรวจสอบความถูกต้อง
- ข้อมูลที่ไม่ผ่านการตรวจสอบจะถูกข้าม

### **Duplicate Detection:**
- IP Inventory: ตรวจสอบจาก `ip_address`
- Subnets: ตรวจสอบจาก `subnet`
- แสดงเฉพาะ fields ที่มีความแตกต่าง

## 📊 Sample Data Files

ระบบมีไฟล์ตัวอย่างพร้อมใช้งาน:

### **`sample_ip_inventory.csv`**
- 20 รายการ IP addresses ตัวอย่าง
- ครอบคลุม 3 subnets หลัก
- มีทั้ง used, available, และ reserved IPs
- ครอบคลุม multiple VRFs

### **`sample_subnets.csv`**
- 8 subnets ตัวอย่าง
- ครอบคลุม sections ต่างๆ (Corporate, Management, DMZ, etc.)
- การกำหนดค่า VLAN, devices, VRFs
- ตัวอย่าง nameservers และ threshold settings

## 🚀 Best Practices

1. **ทดสอบก่อน**: ใช้ไฟล์ข้อมูลเล็กๆ ทดสอบก่อน
2. **Backup Data**: สำรองข้อมูลก่อนการ import ขนาดใหญ่
3. **ใช้ Ask Mode**: เพื่อควบคุมการจัดการ duplicates
4. **ตรวจสอบ Log**: อ่าน error messages อย่างละเอียด
5. **Incremental Import**: แบ่ง import เป็นส่วนๆ สำหรับข้อมูลขนาดใหญ่

## 🆘 Troubleshooting

### **Common Issues:**

**"Invalid IP address"**
- ตรวจสอบรูปแบบ IP (x.x.x.x)
- ลบ space หรือ special characters

**"Invalid subnet"**
- ใช้รูปแบบ CIDR (192.168.1.0/24)
- ตรวจสอบ subnet mask ที่ถูกต้อง

**"File too large"**
- แบ่งไฟล์เป็นส่วนๆ (<16MB)
- ลบ columns ที่ไม่จำเป็น

**"Encoding issues"**
- บันทึกไฟล์เป็น UTF-8
- ใช้ text editor ที่รองรับ Unicode

## 📞 Support

หากพบปัญหาการใช้งาน กรุณาตรวจสอบ:
1. Format ของไฟล์ CSV
2. ขนาดไฟล์
3. Error messages ในระบบ
4. Log files ของ server
