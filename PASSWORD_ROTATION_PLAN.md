# Password Rotation Plan - Mongrel Price Ticker

**Date:** $(date)  
**Priority:** 🔴 **CRITICAL - IMMEDIATE ACTION REQUIRED**

## 🚨 **EXPOSED CREDENTIALS REQUIRING IMMEDIATE ROTATION**

### **1. Database Credentials** 🔴
- **Current Password:** `taan2#IbizaI`
- **Exposed In:** 5 Python files (now fixed with environment variables)
- **Risk Level:** CRITICAL
- **Action Required:** IMMEDIATE

### **2. ShipHero Credentials** 🔴
- **Email:** `shipheronatura@gmail.com`
- **Password:** `WQG4SjHzeq9e65a`
- **Exposed In:** 1 Python file (now fixed with environment variables)
- **Risk Level:** CRITICAL
- **Action Required:** IMMEDIATE

## 🔄 **ROTATION PROCEDURE**

### **Step 1: Database Password Rotation**

#### **1.1 Change Database Password**
1. **Access your hosting control panel** (where srv1978.hstgr.io is hosted)
2. **Navigate to MySQL/Database management**
3. **Change password for user:** `u488367489_mongrel_data`
4. **Generate a strong new password** (minimum 16 characters, mixed case, numbers, symbols)

#### **1.2 Update Environment Variables**
```bash
# Edit .env file
nano .env

# Update the DB_PASSWORD line
DB_PASSWORD=your_new_strong_password_here
```

#### **1.3 Test Database Connection**
```bash
cd /home/mongreldatalab/mongrel_price_ticker
python3 -c "
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

load_dotenv()
db_host = os.getenv('DB_HOST')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')

try:
    connection_string = f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}'
    engine = create_engine(connection_string, poolclass=NullPool)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1 as test'))
        print('✅ Database connection successful with new password!')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

### **Step 2: ShipHero Password Rotation**

#### **2.1 Change ShipHero Password**
1. **Go to:** https://app.shiphero.com/account/login
2. **Login with current credentials**
3. **Navigate to account settings**
4. **Change password to a strong new password**

#### **2.2 Update Environment Variables**
```bash
# Edit .env file
nano .env

# Update the SHIPHERO_PASSWORD line
SHIPHERO_PASSWORD=your_new_strong_password_here
```

#### **2.3 Test ShipHero Script**
```bash
cd /home/mongreldatalab/mongrel_price_ticker
python3 scripts/data_processing/shiphero_line_items.py
```

## 🔐 **PASSWORD GENERATION GUIDELINES**

### **Strong Password Requirements:**
- **Length:** Minimum 16 characters
- **Complexity:** Mix of uppercase, lowercase, numbers, symbols
- **Uniqueness:** Never used before
- **Examples:**
  - `Kx9#mP2$vL8@nQ4!wR7`
  - `Bz5&hN3*jM6^cF9#tY2`
  - `Qw8$eR5!tY2@uI7*oP4`

### **Password Management:**
- **Store in password manager** (Bitwarden, 1Password, etc.)
- **Never write down passwords**
- **Use different passwords for each service**
- **Rotate every 90 days**

## 📋 **VERIFICATION CHECKLIST**

### **Database Rotation:**
- [ ] New password generated (16+ chars, complex)
- [ ] Password changed in hosting panel
- [ ] `.env` file updated with new password
- [ ] Database connection test successful
- [ ] All scripts tested with new password

### **ShipHero Rotation:**
- [ ] New password generated (16+ chars, complex)
- [ ] Password changed in ShipHero account
- [ ] `.env` file updated with new password
- [ ] ShipHero script tested with new password

### **Security Verification:**
- [ ] Old passwords no longer work
- [ ] All scripts function correctly
- [ ] No hardcoded passwords remain in code
- [ ] Environment variables working properly

## 🚨 **EMERGENCY PROCEDURES**

### **If Database Access is Lost:**
1. **Check hosting panel** for database status
2. **Verify new password** is correct
3. **Test connection** with database tools
4. **Contact hosting support** if needed

### **If ShipHero Access is Lost:**
1. **Use password reset** on ShipHero website
2. **Check email** for reset instructions
3. **Update `.env`** with new password
4. **Test script** functionality

## 📊 **ROTATION SCHEDULE**

### **Immediate (Today):**
- [ ] Rotate database password
- [ ] Rotate ShipHero password
- [ ] Test all systems

### **Regular Schedule:**
- **Every 90 days:** Rotate all passwords
- **Every 30 days:** Review access logs
- **Every 7 days:** Check for security updates

## 🔍 **MONITORING & ALERTING**

### **Set Up Monitoring:**
1. **Database access logs** - Monitor for unusual activity
2. **Failed login attempts** - Alert on multiple failures
3. **Credential usage** - Track when passwords are used
4. **Script execution** - Monitor for errors

### **Alert Conditions:**
- Multiple failed database connections
- Unusual access patterns
- Script execution failures
- Credential usage outside business hours

## 📞 **SUPPORT CONTACTS**

### **Database Issues:**
- **Hosting Provider:** Check srv1978.hstgr.io support
- **Database Admin:** Contact your database administrator

### **ShipHero Issues:**
- **Support:** https://help.shiphero.com/
- **Account Issues:** Contact ShipHero support

### **Security Issues:**
- **Immediate:** Change all passwords
- **Investigation:** Review access logs
- **Prevention:** Implement monitoring

---

**⚠️ URGENT: Complete password rotation within 24 hours**  
**🔒 SECURITY: This is critical for protecting your data**  
**📈 NEXT: Implement monitoring and regular rotation schedule**
