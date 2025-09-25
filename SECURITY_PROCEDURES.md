# Security Procedures - Mongrel Price Ticker

**Date:** $(date)  
**Version:** 1.0  
**Status:** ✅ **IMPLEMENTED**

## 🛡️ **SECURITY OVERVIEW**

This document outlines the security procedures and best practices for the Mongrel Price Ticker project. All team members must follow these procedures to maintain security standards.

## 🔐 **CREDENTIAL MANAGEMENT**

### **Environment Variables**
- **✅ IMPLEMENTED:** All credentials stored in `.env` file
- **✅ IMPLEMENTED:** `.env` file in `.gitignore` (not committed)
- **✅ IMPLEMENTED:** `.env.example` template for team members

### **Required Environment Variables:**
```bash
# Database Configuration
DB_HOST=your_database_host
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_PORT=3306

# ShipHero Configuration
SHIPHERO_EMAIL=your_shiphero_email
SHIPHERO_PASSWORD=your_shiphero_password
```

### **Credential Rules:**
1. **NEVER** hardcode passwords in source code
2. **ALWAYS** use environment variables
3. **NEVER** commit `.env` files to version control
4. **ALWAYS** use strong, unique passwords
5. **ROTATE** passwords every 90 days

## 🔍 **SECURITY CHECKS**

### **Pre-commit Security Scan**
Run before every commit:
```bash
cd /home/mongreldatalab/mongrel_price_ticker
python3 scripts/security/check_passwords.py
```

### **What the Security Check Detects:**
- Hardcoded passwords
- API keys in source code
- Database connection strings with credentials
- Email addresses in code
- Secrets and tokens

### **Security Check Results:**
- **✅ Clean:** No issues found
- **❌ Issues Found:** Review and fix before committing

## 🚨 **INCIDENT RESPONSE**

### **If Credentials are Exposed:**
1. **IMMEDIATELY** change the exposed password
2. **IMMEDIATELY** update `.env` file
3. **IMMEDIATELY** test all affected scripts
4. **REVIEW** access logs for unauthorized use
5. **NOTIFY** team members of the incident

### **If Database is Compromised:**
1. **IMMEDIATELY** change database password
2. **IMMEDIATELY** review database access logs
3. **IMMEDIATELY** check for unauthorized data access
4. **IMMEDIATELY** update all environment files
5. **CONTACT** hosting provider if needed

## 📋 **DAILY SECURITY CHECKLIST**

### **Before Starting Work:**
- [ ] Verify `.env` file exists and is properly configured
- [ ] Test database connection
- [ ] Run security check script
- [ ] Review any new code for hardcoded credentials

### **Before Committing Code:**
- [ ] Run security check script
- [ ] Verify no `.env` files are staged
- [ ] Check for hardcoded passwords
- [ ] Test all scripts with environment variables

### **Weekly Security Tasks:**
- [ ] Review access logs
- [ ] Check for unusual database activity
- [ ] Update dependencies if needed
- [ ] Review team access permissions

## 🔄 **PASSWORD ROTATION SCHEDULE**

### **Immediate (Required):**
- [ ] Rotate database password (exposed in audit)
- [ ] Rotate ShipHero password (exposed in audit)
- [ ] Update all `.env` files
- [ ] Test all scripts

### **Regular Schedule:**
- **Every 90 days:** Rotate all passwords
- **Every 30 days:** Review access logs
- **Every 7 days:** Check for security updates

## 🛠️ **DEVELOPMENT WORKFLOW**

### **Setting Up New Environment:**
1. **Copy** `.env.example` to `.env`
2. **Fill in** actual credentials
3. **Test** database connection
4. **Run** security check
5. **Verify** all scripts work

### **Adding New Credentials:**
1. **Add** to `.env` file
2. **Add** to `.env.example` (with placeholder)
3. **Update** code to use `os.getenv()`
4. **Test** functionality
5. **Run** security check

### **Code Review Process:**
1. **Check** for hardcoded credentials
2. **Verify** environment variables are used
3. **Test** security check script
4. **Review** database connection code
5. **Approve** only if secure

## 📊 **MONITORING & ALERTING**

### **Database Monitoring:**
- Monitor connection attempts
- Track failed login attempts
- Alert on unusual access patterns
- Log all database operations

### **Script Monitoring:**
- Monitor script execution
- Track credential usage
- Alert on script failures
- Log all operations

### **Access Monitoring:**
- Track who accesses what
- Monitor credential changes
- Alert on suspicious activity
- Review logs regularly

## 🎯 **SECURITY TRAINING**

### **Team Training Topics:**
1. **Environment Variables** - How to use them properly
2. **Password Security** - Creating and managing strong passwords
3. **Code Security** - Writing secure code
4. **Incident Response** - What to do when issues occur
5. **Best Practices** - Security guidelines and procedures

### **New Team Member Onboarding:**
1. **Security briefing** - Overview of procedures
2. **Environment setup** - How to configure `.env`
3. **Tool training** - Security check scripts
4. **Practice session** - Hands-on security training
5. **Certification** - Verify understanding

## 📞 **SUPPORT & CONTACTS**

### **Security Issues:**
- **Immediate:** Change all passwords
- **Investigation:** Review logs and access patterns
- **Prevention:** Update procedures and training

### **Technical Support:**
- **Database:** Check hosting provider support
- **Scripts:** Review error logs and environment
- **Tools:** Check documentation and examples

### **Emergency Contacts:**
- **Team Lead:** [Your team lead contact]
- **Database Admin:** [Your database admin contact]
- **Hosting Support:** [Your hosting provider support]

## 📈 **SECURITY METRICS**

### **Key Performance Indicators:**
- **Zero** hardcoded passwords in code
- **100%** of credentials in environment variables
- **Zero** security incidents
- **100%** team compliance with procedures

### **Monthly Security Report:**
- Number of security checks run
- Number of issues found and fixed
- Password rotation status
- Access log reviews
- Team training completion

---

**🛡️ SECURITY IS EVERYONE'S RESPONSIBILITY**  
**🔒 FOLLOW THESE PROCEDURES TO PROTECT OUR DATA**  
**📈 CONTINUOUS IMPROVEMENT IS KEY TO SECURITY**
