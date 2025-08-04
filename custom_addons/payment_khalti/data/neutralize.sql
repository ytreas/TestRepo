-- disable hitpay payment provider
UPDATE payment_provider
   SET khalti_auth_key = NULL;
