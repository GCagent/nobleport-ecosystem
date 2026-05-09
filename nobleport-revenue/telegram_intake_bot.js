const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const INTAKE_API_URL = process.env.INTAKE_API_URL || 'https://nobleport.io';

if (!TELEGRAM_BOT_TOKEN) {
  console.error('[Telegram] TELEGRAM_BOT_TOKEN not set. Exiting.');
  process.exit(1);
}

const API_BASE = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}`;
let offset = 0;

async function sendMessage(chatId, text) {
  await fetch(`${API_BASE}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'Markdown' }),
  });
}

async function handleMessage(msg) {
  const chatId = msg.chat.id;
  const text = (msg.text || '').trim();

  if (text === '/start') {
    await sendMessage(chatId, '*NoblePort Intake Bot*\n\nCommands:\n/lead <name> — Submit a new lead\n/status <dealId> — Check deal status\n/health — System check');
    return;
  }

  if (text === '/health') {
    try {
      const res = await fetch(`${INTAKE_API_URL}/api/leadboard/health`);
      const data = await res.json();
      await sendMessage(chatId, `System: ${data.status}\nHubSpot: ${data.hubspot_configured ? 'Connected' : 'Not configured'}`);
    } catch (err) {
      await sendMessage(chatId, `System check failed: ${err.message}`);
    }
    return;
  }

  if (text.startsWith('/lead ')) {
    const name = text.slice(6).trim();
    if (!name) { await sendMessage(chatId, 'Usage: /lead <name>'); return; }
    await sendMessage(chatId, `Lead received: *${name}*\nRouting to LeadIntakeAgent...`);
    console.log(`[Telegram] Lead submitted: ${name} from chat ${chatId}`);
    return;
  }

  if (text.startsWith('/status ')) {
    const dealId = text.slice(8).trim();
    try {
      const res = await fetch(`${INTAKE_API_URL}/api/leadboard/deals/${dealId}`);
      const data = await res.json();
      if (data.error) { await sendMessage(chatId, `Error: ${data.error}`); return; }
      const p = data.properties || {};
      await sendMessage(chatId, `*${p.dealname || 'Unknown'}*\nStage: ${p.dealstage}\nAmount: $${p.amount || '0'}`);
    } catch (err) {
      await sendMessage(chatId, `Lookup failed: ${err.message}`);
    }
    return;
  }

  await sendMessage(chatId, 'Type /start for available commands.');
}

async function poll() {
  try {
    const res = await fetch(`${API_BASE}/getUpdates?offset=${offset}&timeout=30`);
    const data = await res.json();
    if (data.ok && data.result.length > 0) {
      for (const update of data.result) {
        offset = update.update_id + 1;
        if (update.message) await handleMessage(update.message);
      }
    }
  } catch (err) {
    console.error(`[Telegram] Poll error: ${err.message}`);
    await new Promise(r => setTimeout(r, 5000));
  }
  poll();
}

console.log('[Telegram] NoblePort Intake Bot starting...');
poll();
