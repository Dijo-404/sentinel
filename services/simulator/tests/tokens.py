WORKFLOW = {"Authorization": "Bearer tok-workflow-demo"}
VERIFIER = {"Authorization": "Bearer tok-verifier-demo"}
DISPATCHER = {"Authorization": "Bearer tok-dispatcher-demo"}
ADMIN = {"Authorization": "Bearer tok-sandbox-admin-demo"}

REFUND_BODY = {
    "action_id": "action-demo-1",
    "provider_ref": "refund-demo-1",
    "transaction_ref": "TXN-B",
    "amount_minor": 150000,
    "currency": "INR",
    "destination": "ORIGINAL_PAYMENT_ROUTE",
}
