import Stripe from 'https://esm.sh/stripe@14?target=denonext'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const stripe = new Stripe(Deno.env.get('STRIPE_API_KEY') as string, {
  apiVersion: '2024-11-20'
})
const cryptoProvider = Stripe.createSubtleCryptoProvider()

const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
)

// ── Price ID → subscription_type map ──
const PRICE_MAP: Record<string, string> = {
  'price_1T60BQLWG769Pv4apChlmFls': 'monthly',
  'price_1T60C5LWG769Pv4aJ7beMvHg': 'season_pass',
  'price_1T6GIqLWG769Pv4aEBoXjLgq': 'annual_pass',
}

function getSubType(session: Stripe.Checkout.Session): string {
  // Try to get price ID from line items if already expanded
  const priceId = (session as any).line_items?.data?.[0]?.price?.id
  if (priceId && PRICE_MAP[priceId]) return PRICE_MAP[priceId]
  // Fallback: use mode
  return session.mode === 'subscription' ? 'monthly' : 'season_pass'
}

Deno.serve(async (request) => {
  const signature = request.headers.get('Stripe-Signature')
  const body = await request.text()

  let event
  try {
    event = await stripe.webhooks.constructEventAsync(
      body,
      signature!,
      Deno.env.get('STRIPE_WEBHOOK_SIGNING_SECRET')!,
      undefined,
      cryptoProvider
    )
  } catch (err) {
    return new Response(err.message, { status: 400 })
  }

  console.log(`🔔 Event received: ${event.type}`)

  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object as Stripe.Checkout.Session
      const customerId = session.customer as string
      const userId = session.metadata?.supabase_user_id

      // Expand line items to get price ID
      let expandedSession = session
      try {
        expandedSession = await stripe.checkout.sessions.retrieve(session.id, {
          expand: ['line_items'],
        })
      } catch (e) {
        console.warn('Could not expand line items:', e)
      }

      const subType = getSubType(expandedSession)
      console.log(`💳 subType resolved: ${subType}`)

      if (userId) {
        const { error } = await supabase
          .from('profiles')
          .update({
            subscription_status: 'active',
            stripe_customer_id: customerId,
            subscription_type: subType,
            subscription_updated_at: new Date().toISOString()
          })
          .eq('id', userId)
        if (error) console.error('Update error:', error.message)
      } else {
        // Fallback: look up user by email
        const customerEmail = session.customer_details?.email
        console.log(`No user ID in metadata, trying email: ${customerEmail}`)

        const { data: users } = await supabase.auth.admin.listUsers()
        const user = users?.users?.find(u => u.email === customerEmail)

        if (user) {
          const { error } = await supabase
            .from('profiles')
            .update({
              subscription_status: 'active',
              stripe_customer_id: customerId,
              subscription_type: subType,
              subscription_updated_at: new Date().toISOString()
            })
            .eq('id', user.id)
          if (error) console.error('Update error:', error.message)
        } else {
          console.error('No user found for email:', customerEmail)
        }
      }
      break
    }

    case 'customer.subscription.deleted': {
      const subscription = event.data.object as Stripe.Subscription
      const customerId = subscription.customer as string

      const { error } = await supabase
        .from('profiles')
        .update({
          subscription_status: 'cancelled',
          subscription_updated_at: new Date().toISOString()
        })
        .eq('stripe_customer_id', customerId)

      if (error) console.error('Cancel error:', error.message)
      break
    }

    case 'invoice.payment_failed': {
      const invoice = event.data.object as Stripe.Invoice
      const customerId = invoice.customer as string

      const { error } = await supabase
        .from('profiles')
        .update({
          subscription_status: 'past_due',
          subscription_updated_at: new Date().toISOString()
        })
        .eq('stripe_customer_id', customerId)

      if (error) console.error('Past due error:', error.message)
      break
    }
  }

  return new Response(JSON.stringify({ ok: true }), { status: 200 })
})
