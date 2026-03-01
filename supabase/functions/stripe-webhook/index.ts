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
      const mode = session.mode
      const userId = session.metadata?.supabase_user_id

      const subType = mode === 'subscription' ? 'monthly' : 'season_pass'

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
        // Fallback: look up user by email in auth.users
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
