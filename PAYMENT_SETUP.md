# Payment Setup

This app uses Toss Payments for buying points.

## Flow

1. User clicks `+ 충전하기`.
2. The app creates a `point_orders` row with status `pending`.
3. Toss Payments opens the payment window.
4. Toss redirects to `/payment/success`.
5. `/payment/success` calls the Supabase Edge Function `confirm-toss-payment`.
6. The Edge Function confirms the payment with Toss Payments.
7. `confirm_point_payment` marks the order as `paid`, adds points, and writes a `transactions` row.

## Required Supabase SQL

Run these files in Supabase SQL Editor:

1. `point_payment.sql`
2. `charge_point.sql`

`point_payment.sql` creates `point_orders`, `create_point_order`, and `confirm_point_payment`.
`charge_point.sql` locks the old direct top-up RPC so it can only run from the server role.

## Required Environment Variables

Nuxt client:

```env
NUXT_PUBLIC_TOSS_PAYMENTS_CLIENT_KEY=test_ck_...
```

Supabase Edge Function secret:

```sh
supabase secrets set TOSS_PAYMENTS_SECRET_KEY=test_sk_...
```

Use Toss test keys while developing. Switch to live keys only after the test payment flow is fully verified.

## Deploy Edge Function

```sh
supabase functions deploy confirm-toss-payment
```

## Test Checklist

1. Log in.
2. Click `+ 충전하기`.
3. Enter a point amount, for example `10000`.
4. Complete Toss test payment.
5. Confirm `/payment/success` shows success.
6. Confirm header points increase.
7. Confirm `point_orders.status = 'paid'`.
8. Confirm `transactions` has a `charge` row.
