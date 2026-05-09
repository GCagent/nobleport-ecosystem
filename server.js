require('dotenv').config();
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// CRITICAL: stripeWebhook BEFORE express.json() — raw body needed for signature verification
const { stripeWebhookRouter } = require('./nobleport-revenue/stripe_webhook_handler');
app.use('/api/webhooks', stripeWebhookRouter);

// JSON parsing AFTER webhook router
app.use(express.json());

// LeadBoard API
const leadboard = require('./leadboard-live/leadboard_api');
app.use(leadboard);

// Static files
app.use(express.static(path.join(__dirname)));

// Health check
app.get('/api/health', (_req, res) => {
  res.json({
    status: 'ok',
    version: '1.0.0',
    services: {
      leadboard: true,
      stripe_webhooks: true,
      telegram_bot: !!process.env.TELEGRAM_BOT_TOKEN,
    },
  });
});

app.listen(PORT, () => {
  console.log(`\n  NoblePort Server live on http://0.0.0.0:${PORT}`);
  console.log(`  LeadBoard API:     http://0.0.0.0:${PORT}/api/leadboard/health`);
  console.log(`  Stripe Webhooks:   http://0.0.0.0:${PORT}/api/webhooks/stripe`);
  console.log(`  Dashboard:         http://0.0.0.0:${PORT}/`);
  console.log(`  Command Center:    http://0.0.0.0:${PORT}/command-center/\n`);
});
