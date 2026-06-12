-- M-089: Facebook Messenger channel support (PostgreSQL)
-- Lei No 001: PostgreSQL é fonte única da verdade

ALTER TABLE lotoia_clients
  ADD COLUMN IF NOT EXISTS messenger_psid VARCHAR(64) UNIQUE,
  ADD COLUMN IF NOT EXISTS channel VARCHAR(20) DEFAULT 'whatsapp';
-- channel: 'whatsapp' | 'messenger'

CREATE INDEX IF NOT EXISTS idx_clients_messenger_psid
  ON lotoia_clients(messenger_psid);

ALTER TABLE lotoia_client_generations
  ADD COLUMN IF NOT EXISTS channel VARCHAR(20) DEFAULT 'whatsapp';

ALTER TABLE generation_events
  ADD COLUMN IF NOT EXISTS channel VARCHAR(20) DEFAULT 'whatsapp';

ALTER TABLE leads
  ADD COLUMN IF NOT EXISTS messenger_psid VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_leads_messenger_psid
  ON leads(messenger_psid);
