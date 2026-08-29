-- remove-your-data legal log
-- Source of truth for a household takedown workspace. Never commit this DB.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE IF NOT EXISTS person (
  id INTEGER PRIMARY KEY,
  legal_name TEXT NOT NULL,
  residency_country TEXT NOT NULL,
  residency_region TEXT,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  cadence_hours INTEGER NOT NULL DEFAULT 168,
  anonymity_mode TEXT NOT NULL DEFAULT 'dedicated'
    CHECK (anonymity_mode IN ('dedicated', 'personal', 'max')),
  household_scope INTEGER NOT NULL DEFAULT 0,
  relationship TEXT NOT NULL DEFAULT 'self',
  consent_basis TEXT NOT NULL DEFAULT 'self',
  active INTEGER NOT NULL DEFAULT 1,
  drop_filed INTEGER NOT NULL DEFAULT 0,
  intake_complete INTEGER NOT NULL DEFAULT 0,
  created_at_utc TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS identifier (
  id INTEGER PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES person(id),
  kind TEXT NOT NULL,
  value TEXT NOT NULL,
  normalized TEXT NOT NULL,
  scan INTEGER NOT NULL DEFAULT 1,
  notes TEXT,
  UNIQUE (person_id, kind, normalized)
);

CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS broker (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  family TEXT,
  optout_url TEXT,
  channel TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS listing (
  id INTEGER PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES person(id),
  broker_id INTEGER REFERENCES broker(id),
  url TEXT NOT NULL,
  found_via TEXT,
  pii_shown TEXT,
  status TEXT NOT NULL DEFAULT 'found'
    CHECK (status IN (
      'found', 'filed', 'pending_verify', 'pending_drop',
      'gone', 'leftover', 'blocked'
    )),
  email_used TEXT,
  request_id TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL,
  UNIQUE (person_id, url)
);

CREATE TABLE IF NOT EXISTS action_log (
  id INTEGER PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES person(id),
  listing_id INTEGER REFERENCES listing(id),
  broker_id INTEGER REFERENCES broker(id),
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  channel TEXT,
  request_id TEXT,
  result TEXT,
  evidence_path TEXT,
  listing_url TEXT,
  occurred_at_utc TEXT NOT NULL,
  occurred_at_local TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clock (
  id INTEGER PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES person(id),
  listing_id INTEGER REFERENCES listing(id),
  broker_id INTEGER REFERENCES broker(id),
  kind TEXT NOT NULL
    CHECK (kind IN (
      'verify_email', 'site_window', 'legal_response',
      'drop_45d', 'drop_90d', 'rescan'
    )),
  legal_basis TEXT,
  started_at_utc TEXT NOT NULL,
  due_at_utc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'done', 'overdue', 'waived')),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS email_event (
  id INTEGER PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES person(id),
  listing_id INTEGER REFERENCES listing(id),
  mailbox TEXT NOT NULL,
  from_domain TEXT,
  subject TEXT,
  received_at_utc TEXT,
  had_code_or_link INTEGER NOT NULL DEFAULT 0,
  handled INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS leftover (
  id INTEGER PRIMARY KEY,
  listing_id INTEGER NOT NULL REFERENCES listing(id),
  why TEXT NOT NULL,
  next_step TEXT NOT NULL,
  open INTEGER NOT NULL DEFAULT 1,
  updated_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_listing_status ON listing(person_id, status);
CREATE INDEX IF NOT EXISTS idx_clock_due ON clock(status, due_at_utc);
CREATE INDEX IF NOT EXISTS idx_action_when ON action_log(occurred_at_utc);
CREATE INDEX IF NOT EXISTS idx_ident_person ON identifier(person_id, kind);

CREATE VIEW IF NOT EXISTS v_evidence_chronology AS
SELECT
  a.occurred_at_utc,
  a.occurred_at_local,
  a.actor,
  p.legal_name AS person,
  b.name AS broker,
  a.listing_url,
  a.action,
  a.channel,
  a.request_id,
  a.result,
  a.evidence_path,
  a.person_id
FROM action_log a
JOIN person p ON p.id = a.person_id
LEFT JOIN broker b ON b.id = a.broker_id;

CREATE VIEW IF NOT EXISTS v_open_clocks AS
SELECT
  c.id,
  p.legal_name AS person,
  c.kind,
  c.legal_basis,
  c.due_at_utc,
  c.status,
  l.url AS listing_url,
  b.name AS broker,
  c.notes,
  c.person_id
FROM clock c
JOIN person p ON p.id = c.person_id
LEFT JOIN listing l ON l.id = c.listing_id
LEFT JOIN broker b ON b.id = c.broker_id
WHERE c.status IN ('open', 'overdue')
ORDER BY c.due_at_utc ASC;
