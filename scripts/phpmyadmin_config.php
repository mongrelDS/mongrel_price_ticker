<?php
/**
 * Custom phpMyAdmin Configuration for Mongrel Price Ticker
 * Place this file in: /etc/phpmyadmin/conf.d/mongrel_config.php
 */

// Security settings
$cfg['ForceSSL'] = false; // Set to true in production
$cfg['CheckConfigurationPermissions'] = true;
$cfg['CheckPermissions'] = true;
$cfg['AllowArbitraryServer'] = false;
$cfg['ArbitraryServerRegexp'] = '';

// Hide sensitive information
$cfg['ShowServerInfo'] = false;
$cfg['ShowPhpInfo'] = false;
$cfg['ShowChgPassword'] = false;
$cfg['ShowCreateDb'] = false;

// Session security
$cfg['LoginCookieValidity'] = 1800; // 30 minutes
$cfg['LoginCookieRecall'] = true;
$cfg['LoginCookieDeleteAll'] = true;

// Blowfish secret (generate a random 32-character string)
$cfg['blowfish_secret'] = 'mongrel_price_ticker_secret_key_2024';

// Server configuration
$i = 0;
$i++;

// Database server configuration
$cfg['Servers'][$i]['host'] = 'localhost';
$cfg['Servers'][$i]['port'] = '3306';
$cfg['Servers'][$i]['socket'] = '';
$cfg['Servers'][$i]['ssl_key'] = '';
$cfg['Servers'][$i]['ssl_cert'] = '';
$cfg['Servers'][$i]['ssl_ca'] = '';
$cfg['Servers'][$i]['ssl_ciphers'] = '';
$cfg['Servers'][$i]['ssl_verify'] = false;
$cfg['Servers'][$i]['compress'] = false;

// Authentication method
$cfg['Servers'][$i]['auth_type'] = 'cookie';
$cfg['Servers'][$i]['user'] = '';
$cfg['Servers'][$i]['password'] = '';

// Security settings
$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['Servers'][$i]['AllowRoot'] = false;
$cfg['Servers'][$i]['DisableIS'] = false;

// Advanced features
$cfg['Servers'][$i]['pmadb'] = 'phpmyadmin';
$cfg['Servers'][$i]['bookmarktable'] = 'pma__bookmark';
$cfg['Servers'][$i]['relation'] = 'pma__relation';
$cfg['Servers'][$i]['table_info'] = 'pma__table_info';
$cfg['Servers'][$i]['table_coords'] = 'pma__table_coords';
$cfg['Servers'][$i]['pdf_pages'] = 'pma__pdf_pages';
$cfg['Servers'][$i]['column_info'] = 'pma__column_info';
$cfg['Servers'][$i]['history'] = 'pma__history';
$cfg['Servers'][$i]['table_uiprefs'] = 'pma__table_uiprefs';
$cfg['Servers'][$i]['tracking'] = 'pma__tracking';
$cfg['Servers'][$i]['userconfig'] = 'pma__userconfig';
$cfg['Servers'][$i]['recent'] = 'pma__recent';
$cfg['Servers'][$i]['favorite'] = 'pma__favorites';
$cfg['Servers'][$i]['users'] = 'pma__users';
$cfg['Servers'][$i]['usergroups'] = 'pma__usergroups';
$cfg['Servers'][$i]['navigationhiding'] = 'pma__navigationhiding';
$cfg['Servers'][$i]['savedsearches'] = 'pma__savedsearches';
$cfg['Servers'][$i]['central_columns'] = 'pma__central_columns';
$cfg['Servers'][$i]['designer_settings'] = 'pma__designer_settings';
$cfg['Servers'][$i]['export_templates'] = 'pma__export_templates';

// Custom settings for Mongrel Price Ticker
$cfg['MaxRows'] = 50; // Limit rows displayed for better performance
$cfg['MaxTableList'] = 100;
$cfg['MaxCharactersInDisplayedSQL'] = 1000;

// Theme settings
$cfg['ThemeDefault'] = 'pmahomme';
$cfg['ThemeManager'] = true;

// Language settings
$cfg['DefaultLang'] = 'en';
$cfg['Lang'] = 'en';

// Export settings
$cfg['Export']['method'] = 'quick';
$cfg['Export']['format'] = 'sql';

// Import settings
$cfg['Import']['format'] = 'sql';
$cfg['Import']['charset'] = 'utf-8';

echo "Mongrel Price Ticker phpMyAdmin configuration loaded successfully!";
?>
