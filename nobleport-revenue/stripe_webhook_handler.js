const express = require('express');
const Stripe = require('stripe');

const router = express.Router();
const stripeKey = process.env.STRIPE_SECRET_KEY;
const endpointSecret = process.env.STRIPE_WEBHOOK_SECRET;
const stripe = stripeKey ? Stripe(stripeKey) : null;

router.post('/stripe', express.raw({ type: 'application/json' }), (req, res) => {
  if (!stripe) {
    console.warn('[Stripe] STRIPE_SECRET_KEY not configured — webhook ignored');
    return res.status(503).json({ error: 'Stripe not configured' });
  }
  let event;
  try {
    if (endpointSecret) {
      const sig = req.headers['stripe-signature'];
      event = stripe.webhooks.constructEvent(req.body, sig, endpointSecret);
    } else {
      event = JSON.parse(req.body);
      console.warn('[Stripe] No STRIPE_WEBHOOK_SECRET set — signature not verified');
    }
  } catch (err) {
    console.error(`[Stripe] Webhook signature verification failed: ${err.message}`);
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  console.log(`[Stripe] Event received: ${event.type} (${event.id})`);

  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object;
      console.log(`[Stripe] Checkout completed: ${session.id}, amount: ${session.amount_total}, customer: ${session.customer_email}`);
      break;
    }
    case 'payment_intent.succeeded': {
      const pi = event.data.object;
      console.log(`[Stripe] Payment succeeded: ${pi.id}, amount: ${pi.amount}, currency: ${pi.currency}`);
      break;
    }
    case 'invoice.paid': {
      const invoice = event.data.object;
      console.log(`[Stripe] Invoice paid: ${invoice.id}, amount: ${invoice.amount_paid}, customer: ${invoice.customer}`);
      break;
    }
    case 'invoice.payment_failed': {
      const invoice = event.data.object;
      console.error(`[Stripe] Payment FAILED: ${invoice.id}, customer: ${invoice.customer}`);
      break;
    }
    default:
      console.log(`[Stripe] Unhandled event type: ${event.type}`);
  }

  res.json({ received: true });
});

module.exports = { stripeWebhookRouter: router };
