const express = require('express');
const router = express.Router();

const HUBSPOT_API_KEY = process.env.HUBSPOT_API_KEY;
const HUBSPOT_BASE = 'https://api.hubapi.com/crm/v3/objects/deals';

async function hubspotFetch(path, options = {}) {
  const res = await fetch(`${HUBSPOT_BASE}${path}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${HUBSPOT_API_KEY}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HubSpot ${res.status}: ${body}`);
  }
  return res.json();
}

router.get('/api/leadboard/deals', async (req, res) => {
  try {
    const data = await hubspotFetch('?limit=20&properties=dealname,dealstage,amount,pipeline');
    res.json({ deals: data.results });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

router.get('/api/leadboard/deals/:dealId', async (req, res) => {
  try {
    const data = await hubspotFetch(
      `/${req.params.dealId}?properties=dealname,dealstage,amount,pipeline,closed_lost_reason`
    );
    res.json(data);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

router.post('/api/leadboard/deals/:dealId/stage', async (req, res) => {
  const { stage, closed_lost_reason } = req.body;
  if (!stage) return res.status(400).json({ error: 'stage is required' });

  const properties = { dealstage: stage };
  if (closed_lost_reason) properties.closed_lost_reason = closed_lost_reason;

  try {
    const data = await hubspotFetch(`/${req.params.dealId}`, {
      method: 'PATCH',
      body: JSON.stringify({ properties }),
    });
    console.log(`[LeadBoard] Deal ${req.params.dealId} → ${stage}`);
    res.json({ success: true, deal: data });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

router.get('/api/leadboard/health', (_req, res) => {
  res.json({ status: 'ok', hubspot_configured: !!HUBSPOT_API_KEY });
});

module.exports = router;
