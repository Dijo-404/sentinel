WORKFLOW = {"Authorization": "Bearer tok-workflow"}
VERIFIER = {"Authorization": "Bearer tok-verifier"}
DISPATCHER = {"Authorization": "Bearer tok-dispatcher"}
ADMIN = {"Authorization": "Bearer tok-sandbox-admin"}

REFUND_BODY = {
    "action_id": "action-demo-1",
    "provider_ref": "refund-demo-1",
    "transaction_ref": "TXN-B",
    "amount_minor": 150000,
    "currency": "INR",
    "destination": "ORIGINAL_PAYMENT_ROUTE",
}
