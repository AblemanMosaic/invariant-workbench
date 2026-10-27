-- Experimental local reference schema. Explicit setup only; no automatic migration.
-- The application role is a trusted writer. This is NOT an all-writer boundary.
CREATE SCHEMA IF NOT EXISTS miw_reference;
CREATE TABLE IF NOT EXISTS miw_reference.tenants (
    tenant text PRIMARY KEY,
    state jsonb NOT NULL CHECK (jsonb_typeof(state) = 'object')
);
CREATE TABLE IF NOT EXISTS miw_reference.receipts (
    tenant text NOT NULL REFERENCES miw_reference.tenants(tenant),
    operation_id text NOT NULL,
    request_root text NOT NULL CHECK (length(request_root) = 64),
    receipt jsonb NOT NULL CHECK (jsonb_typeof(receipt) = 'object'),
    PRIMARY KEY (tenant, operation_id)
);
REVOKE ALL ON SCHEMA miw_reference FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA miw_reference FROM PUBLIC;
