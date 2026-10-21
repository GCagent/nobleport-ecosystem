-- ============================================================================
-- NoblePort Schema: 14 Core Tables
-- Run against Supabase Postgres (requires auth schema from Supabase)
-- ============================================================================

-- 1. companies (tenant/org boundary)
create table if not exists companies (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    domain text unique,
    settings jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 2. profiles (tied to auth.users)
create table if not exists profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    email text unique,
    full_name text,
    role text not null check (role in ('gc', 'inspector', 'municipal', 'arbiter', 'admin')),
    company_id uuid references companies(id) on delete set null,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 3. projects
create table if not exists projects (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    status text not null default 'pending'
        check (status in ('pending', 'active', 'on_hold', 'completed', 'cancelled')),
    gc_id uuid not null references profiles(id),
    company_id uuid references companies(id) on delete set null,
    address text,
    city text,
    state text,
    zip_code text,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 4. project_members (team access)
create table if not exists project_members (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references projects(id) on delete cascade,
    user_id uuid not null references profiles(id) on delete cascade,
    role text not null default 'viewer'
        check (role in ('owner', 'manager', 'member', 'viewer')),
    added_at timestamptz not null default now(),
    unique (project_id, user_id)
);

-- 5. permits
create table if not exists permits (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references projects(id) on delete cascade,
    permit_type text not null
        check (permit_type in ('building', 'electrical', 'plumbing', 'mechanical', 'demolition', 'grading', 'other')),
    permit_number text unique,
    status text not null default 'applied'
        check (status in ('applied', 'under_review', 'approved', 'denied', 'expired', 'revoked')),
    issued_by uuid references profiles(id),
    issued_at timestamptz,
    expires_at timestamptz,
    notes text,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 6. inspections
create table if not exists inspections (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references projects(id) on delete cascade,
    permit_id uuid references permits(id) on delete set null,
    inspector_id uuid references profiles(id),
    inspection_type text not null default 'general'
        check (inspection_type in ('general', 'foundation', 'framing', 'electrical', 'plumbing', 'mechanical', 'final', 'other')),
    status text not null default 'scheduled'
        check (status in ('scheduled', 'in_progress', 'passed', 'failed', 'cancelled', 'rescheduled')),
    notes text,
    result_notes text,
    scheduled_at timestamptz,
    completed_at timestamptz,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 7. inspection_items (checklist within an inspection)
create table if not exists inspection_items (
    id uuid primary key default gen_random_uuid(),
    inspection_id uuid not null references inspections(id) on delete cascade,
    description text not null,
    passed boolean,
    notes text,
    sort_order integer not null default 0,
    created_at timestamptz not null default now()
);

-- 8. documents (attachments)
create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    project_id uuid references projects(id) on delete cascade,
    inspection_id uuid references inspections(id) on delete set null,
    permit_id uuid references permits(id) on delete set null,
    uploaded_by uuid not null references profiles(id),
    file_name text not null,
    file_path text not null,
    file_size_bytes bigint,
    mime_type text,
    doc_type text default 'other'
        check (doc_type in ('plan', 'photo', 'report', 'permit_doc', 'certificate', 'other')),
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- 9. disputes
create table if not exists disputes (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references projects(id) on delete cascade,
    inspection_id uuid references inspections(id) on delete set null,
    raised_by uuid not null references profiles(id),
    assigned_arbiter uuid references profiles(id),
    status text not null default 'open'
        check (status in ('open', 'under_review', 'resolved', 'escalated', 'closed')),
    subject text not null,
    description text,
    resolution text,
    resolved_at timestamptz,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- 10. dispute_comments
create table if not exists dispute_comments (
    id uuid primary key default gen_random_uuid(),
    dispute_id uuid not null references disputes(id) on delete cascade,
    author_id uuid not null references profiles(id),
    body text not null,
    created_at timestamptz not null default now()
);

-- 11. approvals (municipal sign-offs)
create table if not exists approvals (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references projects(id) on delete cascade,
    permit_id uuid references permits(id) on delete set null,
    inspection_id uuid references inspections(id) on delete set null,
    approved_by uuid not null references profiles(id),
    approval_type text not null
        check (approval_type in ('permit_approval', 'inspection_signoff', 'final_occupancy', 'variance', 'other')),
    status text not null default 'pending'
        check (status in ('pending', 'approved', 'denied', 'revoked')),
    notes text,
    approved_at timestamptz,
    metadata jsonb default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- 12. notifications
create table if not exists notifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references profiles(id) on delete cascade,
    title text not null,
    body text,
    link text,
    read boolean not null default false,
    notification_type text default 'info'
        check (notification_type in ('info', 'warning', 'action_required', 'update')),
    created_at timestamptz not null default now()
);

-- 13. audit_log (append-only)
create table if not exists audit_log (
    id uuid primary key default gen_random_uuid(),
    actor_id uuid references profiles(id),
    action text not null,
    table_name text not null,
    record_id uuid,
    old_data jsonb,
    new_data jsonb,
    ip_address inet,
    created_at timestamptz not null default now()
);

-- 14. merkle_anchors
create table if not exists merkle_anchors (
    id uuid primary key default gen_random_uuid(),
    anchor_date date not null,
    root_hash text not null,
    record_count integer not null,
    source_table text not null,
    leaf_hashes text[],
    metadata jsonb default '{}'::jsonb,
    chain_name text,
    tx_hash text,
    anchored_at timestamptz,
    created_at timestamptz not null default now()
);

create unique index if not exists merkle_anchors_unique_daily
on merkle_anchors(anchor_date, source_table);
