-- disable hitpay payment provider
UPDATE payment_provider
   SET esewa_auth_key = NULL;
