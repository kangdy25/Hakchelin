// @ts-nocheck
import { createClient } from 'npm:@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS'
}

type PointOrder = {
  order_id: string
  user_id: string
  amount: number
  point_amount: number
  status: 'pending' | 'paid' | 'failed' | 'cancelled'
}

const jsonResponse = (body: Record<string, unknown>, status = 200) => {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders,
      'Content-Type': 'application/json'
    }
  })
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  if (req.method !== 'POST') {
    return jsonResponse({ error: 'Method not allowed' }, 405)
  }

  const supabaseUrl = Deno.env.get('SUPABASE_URL')
  const anonKey = Deno.env.get('SUPABASE_ANON_KEY')
  const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
  const tossSecretKey = Deno.env.get('TOSS_PAYMENTS_SECRET_KEY')

  if (!supabaseUrl || !anonKey || !serviceRoleKey || !tossSecretKey) {
    return jsonResponse({ error: '결제 서버 환경 변수가 설정되지 않았습니다.' }, 500)
  }

  const authorization = req.headers.get('Authorization') || ''
  if (!authorization.startsWith('Bearer ')) {
    return jsonResponse({ error: '로그인이 필요합니다.' }, 401)
  }

  let payload: { paymentKey?: string; orderId?: string; amount?: number }
  try {
    payload = await req.json()
  } catch {
    return jsonResponse({ error: '요청 본문을 읽을 수 없습니다.' }, 400)
  }

  const paymentKey = String(payload.paymentKey || '')
  const orderId = String(payload.orderId || '')
  const amount = Number(payload.amount || 0)

  if (!paymentKey || !orderId || !amount) {
    return jsonResponse({ error: '결제 승인 정보가 올바르지 않습니다.' }, 400)
  }

  const userClient = createClient(supabaseUrl, anonKey, {
    global: { headers: { Authorization: authorization } }
  })

  const serviceClient = createClient(supabaseUrl, serviceRoleKey)

  const { data: userData, error: userError } = await userClient.auth.getUser()
  if (userError || !userData.user) {
    return jsonResponse({ error: '로그인 정보를 확인할 수 없습니다.' }, 401)
  }

  const { data: orderRow, error: orderError } = await serviceClient
    .from('point_orders')
    .select('order_id, user_id, amount, point_amount, status')
    .eq('order_id', orderId)
    .single()

  const order = orderRow as PointOrder | null

  if (orderError || !order) {
    return jsonResponse({ error: '충전 주문을 찾을 수 없습니다.' }, 404)
  }

  if (order.user_id !== userData.user.id) {
    return jsonResponse({ error: '본인 충전 주문만 승인할 수 있습니다.' }, 403)
  }

  if (order.amount !== amount) {
    return jsonResponse({ error: '결제 금액이 충전 주문과 일치하지 않습니다.' }, 400)
  }

  if (order.status === 'paid') {
    return jsonResponse({ order })
  }

  if (order.status !== 'pending') {
    return jsonResponse({ error: `처리할 수 없는 충전 주문 상태입니다: ${order.status}` }, 400)
  }

  const encodedSecret = btoa(`${tossSecretKey}:`)
  const tossResponse = await fetch('https://api.tosspayments.com/v1/payments/confirm', {
    method: 'POST',
    headers: {
      Authorization: `Basic ${encodedSecret}`,
      'Content-Type': 'application/json',
      'Idempotency-Key': orderId
    },
    body: JSON.stringify({
      paymentKey,
      orderId,
      amount
    })
  })

  const tossResult = await tossResponse.json()

  if (!tossResponse.ok) {
    await serviceClient
      .from('point_orders')
      .update({
        status: 'failed',
        payment_key: paymentKey,
        toss_response: tossResult,
        updated_at: new Date().toISOString()
      })
      .eq('order_id', orderId)

    return jsonResponse(
      {
        error: tossResult?.message || '토스페이먼츠 결제 승인에 실패했습니다.',
        toss: tossResult
      },
      400
    )
  }

  const { data: confirmedOrder, error: confirmError } = await serviceClient.rpc('confirm_point_payment', {
    p_order_id: orderId,
    p_payment_key: paymentKey,
    p_toss_response: tossResult
  })

  if (confirmError) {
    return jsonResponse({ error: confirmError.message }, 500)
  }

  const resultOrder = Array.isArray(confirmedOrder) ? confirmedOrder[0] : confirmedOrder
  return jsonResponse({ order: resultOrder, payment: tossResult })
})
