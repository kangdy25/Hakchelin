# confirm-toss-payment

Supabase Edge Function that confirms a Toss Payments charge and grants points.

Required secrets:

```sh
supabase secrets set TOSS_PAYMENTS_SECRET_KEY=test_sk_...
```

Deploy:

```sh
supabase functions deploy confirm-toss-payment
```

The app calls this function from `/payment/success` after Toss redirects with `paymentKey`, `orderId`, and `amount`.
