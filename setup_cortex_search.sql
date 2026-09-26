-- ============================================================
-- NorthStar CX - Cortex Search Setup
-- STANDALONE script. Does NOT touch CUSTOMERS/POLICIES/CLAIMS/
-- INTERACTIONS tables. Safe to run on its own, anytime, without
-- risk of deleting existing data.
-- Run this in a NEW query, or paste at the bottom of a worksheet
-- and select+run ONLY this block (not the whole file).
-- ============================================================

USE WAREHOUSE NORTHSTAR_WH;
USE DATABASE NORTHSTAR_DB;
USE SCHEMA CORE;

-- Creates a Cortex Search Service over the transcript column,
-- making call transcripts semantically searchable.
-- This does NOT modify the INTERACTIONS table itself - it only
-- reads from it to build a search index.
CREATE OR REPLACE CORTEX SEARCH SERVICE INTERACTIONS_SEARCH
    ON transcript
    ATTRIBUTES customer_id, interaction_id, sentiment, channel, interaction_date
    WAREHOUSE = NORTHSTAR_WH
    TARGET_LAG = '1 hour'
    AS (
        SELECT
            transcript,
            customer_id,
            interaction_id,
            sentiment,
            channel,
            interaction_date
        FROM INTERACTIONS
    );

-- Sanity check: confirm the search service was created
SHOW CORTEX SEARCH SERVICES;
