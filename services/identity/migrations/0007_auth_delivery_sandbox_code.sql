-- Sandbox product-demo inbox: plaintext OTP only when IDENTITY_SANDBOX /
-- SENTINEL_V1_SANDBOX gates persistence. Column stays NULL otherwise.
ALTER TABLE identity.auth_delivery_log
    ADD COLUMN IF NOT EXISTS sandbox_code text;
