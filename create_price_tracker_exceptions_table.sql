-- Create price_tracker_exceptions table
-- This table stores exception data for price tracking

CREATE TABLE IF NOT EXISTS price_tracker_exceptions (
    joined_sku VARCHAR(255) PRIMARY KEY,
    exclude VARCHAR(10) DEFAULT NULL,
    multiple DECIMAL(10,4) DEFAULT NULL,
    est_multiple DECIMAL(10,4) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_exclude (exclude),
    INDEX idx_multiple (multiple),
    INDEX idx_est_multiple (est_multiple)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add some sample data for testing
INSERT IGNORE INTO price_tracker_exceptions (joined_sku, exclude, multiple, est_multiple) VALUES
('SAMPLE_SKU_001', 'no', 1.5, 1.2),
('SAMPLE_SKU_002', 'yes', 0.8, 0.9),
('SAMPLE_SKU_003', NULL, 2.1, 1.8);

-- Verify the table was created
SELECT 'price_tracker_exceptions table created successfully' as status;
SELECT COUNT(*) as row_count FROM price_tracker_exceptions;
