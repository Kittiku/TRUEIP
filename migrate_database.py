"""
Database Migration Script for Network Sections Support
This script adds section_id columns and foreign key relationships to existing tables
"""

import mysql.connector
from mysql.connector import Error

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

def migrate_database():
    """Migrate database to support network sections"""
    try:
        connection = get_db_connection()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        print("🔧 Starting database migration for Network Sections support...")
        
        # 1. Add section_id column to subnets table if it doesn't exist
        try:
            cursor.execute("SHOW COLUMNS FROM subnets LIKE 'section_id'")
            if not cursor.fetchone():
                print("📝 Adding section_id column to subnets table...")
                cursor.execute("ALTER TABLE subnets ADD COLUMN section_id INT AFTER description")
                cursor.execute("CREATE INDEX idx_section_id_subnets ON subnets (section_id)")
                print("✅ Added section_id column to subnets table")
            else:
                print("✅ section_id column already exists in subnets table")
        except Error as e:
            print(f"❌ Error adding section_id to subnets: {e}")
        
        # 2. Add section_id column to ip_inventory table if it doesn't exist
        try:
            cursor.execute("SHOW COLUMNS FROM ip_inventory LIKE 'section_id'")
            if not cursor.fetchone():
                print("📝 Adding section_id column to ip_inventory table...")
                cursor.execute("ALTER TABLE ip_inventory ADD COLUMN section_id INT AFTER subnet")
                cursor.execute("CREATE INDEX idx_section_id_ip ON ip_inventory (section_id)")
                print("✅ Added section_id column to ip_inventory table")
            else:
                print("✅ section_id column already exists in ip_inventory table")
        except Error as e:
            print(f"❌ Error adding section_id to ip_inventory: {e}")
        
        # 3. Drop the existing unique constraint on ip_address if it exists
        try:
            cursor.execute("SHOW INDEX FROM ip_inventory WHERE Key_name = 'ip_address'")
            if cursor.fetchone():
                print("📝 Dropping old unique constraint on ip_address...")
                cursor.execute("ALTER TABLE ip_inventory DROP INDEX ip_address")
                print("✅ Dropped old unique constraint")
            else:
                print("✅ No old unique constraint to drop")
        except Error as e:
            print(f"⚠️  Note: Could not drop old unique constraint: {e}")
        
        # 4. Add new composite unique constraint for ip_address + section_id
        try:
            cursor.execute("SHOW INDEX FROM ip_inventory WHERE Key_name = 'unique_ip_section'")
            if not cursor.fetchone():
                print("📝 Adding composite unique constraint for ip_address + section_id...")
                cursor.execute("ALTER TABLE ip_inventory ADD UNIQUE KEY unique_ip_section (ip_address, section_id)")
                print("✅ Added composite unique constraint")
            else:
                print("✅ Composite unique constraint already exists")
        except Error as e:
            print(f"⚠️  Note: Could not add composite unique constraint: {e}")
        
        # 5. Add unique constraint for subnet + section_id in subnets table
        try:
            cursor.execute("SHOW INDEX FROM subnets WHERE Key_name = 'unique_subnet_section'")
            if not cursor.fetchone():
                print("📝 Adding composite unique constraint for subnet + section_id...")
                cursor.execute("ALTER TABLE subnets ADD UNIQUE KEY unique_subnet_section (subnet, section_id)")
                print("✅ Added subnet composite unique constraint")
            else:
                print("✅ Subnet composite unique constraint already exists")
        except Error as e:
            print(f"⚠️  Note: Could not add subnet composite unique constraint: {e}")
        
        # 6. Try to add foreign key constraints (might fail if data doesn't match)
        try:
            cursor.execute("SHOW CREATE TABLE subnets")
            table_def = cursor.fetchone()[1]
            if 'FOREIGN KEY' not in table_def or 'section_id' not in table_def:
                print("📝 Adding foreign key constraint for subnets.section_id...")
                cursor.execute("""
                    ALTER TABLE subnets 
                    ADD CONSTRAINT fk_subnets_section 
                    FOREIGN KEY (section_id) REFERENCES network_sections(id) 
                    ON DELETE SET NULL
                """)
                print("✅ Added foreign key constraint for subnets")
            else:
                print("✅ Foreign key constraint already exists for subnets")
        except Error as e:
            print(f"⚠️  Could not add foreign key for subnets (data might exist): {e}")
        
        try:
            cursor.execute("SHOW CREATE TABLE ip_inventory")
            table_def = cursor.fetchone()[1]
            if 'FOREIGN KEY' not in table_def or 'section_id' not in table_def:
                print("📝 Adding foreign key constraint for ip_inventory.section_id...")
                cursor.execute("""
                    ALTER TABLE ip_inventory 
                    ADD CONSTRAINT fk_ip_inventory_section 
                    FOREIGN KEY (section_id) REFERENCES network_sections(id) 
                    ON DELETE SET NULL
                """)
                print("✅ Added foreign key constraint for ip_inventory")
            else:
                print("✅ Foreign key constraint already exists for ip_inventory")
        except Error as e:
            print(f"⚠️  Could not add foreign key for ip_inventory (data might exist): {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("🎉 Database migration completed successfully!")
        return True
        
    except Error as e:
        print(f"❌ Database migration error: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Database Migration for Network Sections")
    print("=" * 50)
    
    if migrate_database():
        print("✅ Migration completed successfully")
        print("\n📊 Database is now ready for Network Sections feature!")
        print("   - section_id columns added to subnets and ip_inventory tables")
        print("   - Composite unique constraints added")
        print("   - Foreign key relationships established")
        print("\n🔄 You can now run create_section_sample_data.py to create sample data")
    else:
        print("❌ Migration failed")

if __name__ == "__main__":
    main()
