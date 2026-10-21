-- ============================================================================
-- Enable Row Level Security on all tables
-- ============================================================================

alter table companies enable row level security;
alter table profiles enable row level security;
alter table projects enable row level security;
alter table project_members enable row level security;
alter table permits enable row level security;
alter table inspections enable row level security;
alter table inspection_items enable row level security;
alter table documents enable row level security;
alter table disputes enable row level security;
alter table dispute_comments enable row level security;
alter table approvals enable row level security;
alter table notifications enable row level security;
alter table audit_log enable row level security;
alter table merkle_anchors enable row level security;
