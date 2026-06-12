-- M-092B: Messenger Consultor — estado, leads e canal
-- Lei No 001: PostgreSQL é fonte única da verdade

ALTER TABLE lotoia_clients
  ADD COLUMN IF NOT EXISTS messenger_psid VARCHAR(64) UNIQUE,
  ADD COLUMN IF NOT EXISTS channel        VARCHAR(20) DEFAULT 'whatsapp';

ALTER TABLE leads
  ADD COLUMN IF NOT EXISTS messenger_psid VARCHAR(64),
  ADD COLUMN IF NOT EXISTS facebook_name  VARCHAR(120);

CREATE TABLE IF NOT EXISTS messenger_conversation_state (
  psid              VARCHAR(64)  PRIMARY KEY,
  state             VARCHAR(40)  DEFAULT 'initial',
  free_checks_used  INTEGER      DEFAULT 0,
  last_interaction  TIMESTAMPTZ  DEFAULT NOW(),
  updated_at        TIMESTAMPTZ  DEFAULT NOW()
);

ALTER TABLE lotoia_client_generations
  ADD COLUMN IF NOT EXISTS channel VARCHAR(20) DEFAULT 'whatsapp';

ALTER TABLE generation_events
  ADD COLUMN IF NOT EXISTS channel VARCHAR(20) DEFAULT 'whatsapp';

CREATE INDEX IF NOT EXISTS idx_clients_messenger_psid
  ON lotoia_clients(messenger_psid);
CREATE INDEX IF NOT EXISTS idx_leads_messenger_psid
  ON leads(messenger_psid);
