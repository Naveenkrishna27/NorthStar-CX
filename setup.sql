-- ============================================================
-- NorthStar CX - Snowflake Environment Setup
-- Run this entire script in a Snowsight worksheet.
-- Creates: warehouse, database, schema, and 4 tables matching
-- the CSVs in your data/ folder.
-- ============================================================

-- 1. Warehouse (compute)
CREATE WAREHOUSE IF NOT EXISTS NORTHSTAR_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

-- 2. Database and schema
CREATE DATABASE IF NOT EXISTS NORTHSTAR_DB;
CREATE SCHEMA IF NOT EXISTS NORTHSTAR_DB.CORE;

-- 3. Set context for this session
USE WAREHOUSE NORTHSTAR_WH;
USE DATABASE NORTHSTAR_DB;
USE SCHEMA CORE;

-- 4. Tables (column order/types match the CSV headers exactly)

CREATE OR REPLACE TABLE CUSTOMERS (
    customer_id     VARCHAR(20)   PRIMARY KEY,
    name            VARCHAR(200),
    age             NUMBER,
    city            VARCHAR(200),
    segment         VARCHAR(50),
    tenure_years    NUMBER,
    join_date       DATE,
    email           VARCHAR(200),
    phone           VARCHAR(50)
);

CREATE OR REPLACE TABLE POLICIES (
    policy_id           VARCHAR(20) PRIMARY KEY,
    customer_id         VARCHAR(20) REFERENCES CUSTOMERS(customer_id),
    policy_type         VARCHAR(50),
    annual_premium_inr  NUMBER,
    status              VARCHAR(50),
    renewal_date        DATE
);

CREATE OR REPLACE TABLE CLAIMS (
    claim_id          VARCHAR(20) PRIMARY KEY,
    policy_id         VARCHAR(20) REFERENCES POLICIES(policy_id),
    customer_id       VARCHAR(20) REFERENCES CUSTOMERS(customer_id),
    claim_type        VARCHAR(50),
    claim_amount_inr  NUMBER,
    status            VARCHAR(50),
    claim_date        DATE
);

CREATE OR REPLACE TABLE INTERACTIONS (
    interaction_id     VARCHAR(20) PRIMARY KEY,
    customer_id        VARCHAR(20) REFERENCES CUSTOMERS(customer_id),
    channel            VARCHAR(50),
    sentiment          VARCHAR(20),
    interaction_date   DATE,
    transcript         VARCHAR(2000)
);

-- 5. Quick sanity check - should return 0 rows in each table right now
SELECT 'CUSTOMERS' AS table_name, COUNT(*) AS row_count FROM CUSTOMERS
UNION ALL
SELECT 'POLICIES', COUNT(*) FROM POLICIES
UNION ALL
SELECT 'CLAIMS', COUNT(*) FROM CLAIMS
UNION ALL
SELECT 'INTERACTIONS', COUNT(*) FROM INTERACTIONS;

