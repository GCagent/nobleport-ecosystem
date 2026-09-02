-- ============================================================================
-- RLS Policies for all 14 tables
-- ============================================================================
-- NOTE: Policies on the same table are OR'd together for the same operation.
-- Be deliberate. One weak policy opens the perimeter.
-- ============================================================================


-- ======================== COMPANIES ========================

create policy "companies admin full"
on companies for all
using (public.is_admin())
with check (public.is_admin());

create policy "companies member read own"
on companies for select
using (id = public.current_company_id());


-- ======================== PROFILES ========================

create policy "profiles self read"
on profiles for select
using (id = auth.uid());

create policy "profiles self update"
on profiles for update
using (id = auth.uid())
with check (id = auth.uid());

create policy "profiles admin full"
on profiles for all
using (public.is_admin())
with check (public.is_admin());

-- Same-company users can see each other (for team features)
create policy "profiles same company read"
on profiles for select
using (company_id = public.current_company_id() and company_id is not null);


-- ======================== PROJECTS ========================

-- GC: full access to own projects
create policy "projects gc own"
on projects for all
using (gc_id = auth.uid())
with check (gc_id = auth.uid());

-- GC insert: enforce gc_id = self
create policy "projects gc insert own only"
on projects for insert
with check (gc_id = auth.uid());

-- Inspector: read projects they have inspections on
create policy "projects inspector read assigned"
on projects for select
using (
    exists (
        select 1 from inspections i
        where i.project_id = projects.id
          and i.inspector_id = auth.uid()
    )
);

-- Project member: read projects they belong to
create policy "projects member read"
on projects for select
using (public.is_project_member(id));

-- Municipal: read all projects
create policy "projects municipal read"
on projects for select
using (public.current_app_role() = 'municipal');

-- Arbiter: read all projects
create policy "projects arbiter read"
on projects for select
using (public.current_app_role() = 'arbiter');

-- Admin: full
create policy "projects admin full"
on projects for all
using (public.is_admin())
with check (public.is_admin());

-- Same company read (tenant fence)
create policy "projects same company read"
on projects for select
using (company_id = public.current_company_id() and company_id is not null);


-- ======================== PROJECT_MEMBERS ========================

-- Project owner (GC) can manage members
create policy "project_members gc manage"
on project_members for all
using (
    exists (
        select 1 from projects p
        where p.id = project_members.project_id
          and p.gc_id = auth.uid()
    )
)
with check (
    exists (
        select 1 from projects p
        where p.id = project_members.project_id
          and p.gc_id = auth.uid()
    )
);

-- Members can see their own membership
create policy "project_members self read"
on project_members for select
using (user_id = auth.uid());

-- Admin full
create policy "project_members admin full"
on project_members for all
using (public.is_admin())
with check (public.is_admin());


-- ======================== PERMITS ========================

-- GC: full access to permits on own projects
create policy "permits gc own project"
on permits for all
using (
    exists (
        select 1 from projects p
        where p.id = permits.project_id
          and p.gc_id = auth.uid()
    )
)
with check (
    exists (
        select 1 from projects p
        where p.id = permits.project_id
          and p.gc_id = auth.uid()
    )
);

-- Municipal: read all, update status
create policy "permits municipal read"
on permits for select
using (public.current_app_role() = 'municipal');

create policy "permits municipal update"
on permits for update
using (public.current_app_role() = 'municipal')
with check (public.current_app_role() = 'municipal');

-- Municipal can insert (issue permits)
create policy "permits municipal insert"
on permits for insert
with check (public.current_app_role() = 'municipal');

-- Inspector: read permits on assigned inspections
create policy "permits inspector read assigned"
on permits for select
using (
    exists (
        select 1 from inspections i
        where i.permit_id = permits.id
          and i.inspector_id = auth.uid()
    )
);

-- Admin full
create policy "permits admin full"
on permits for all
using (public.is_admin())
with check (public.is_admin());


-- ======================== INSPECTIONS ========================

-- Inspector: full access to own inspections
create policy "inspections inspector own"
on inspections for all
using (inspector_id = auth.uid())
with check (inspector_id = auth.uid());

-- GC: read inspections on own projects
create policy "inspections gc read project"
on inspections for select
using (
    exists (
        select 1 from projects p
        where p.id = inspections.project_id
          and p.gc_id = auth.uid()
    )
);

-- Municipal: read all, update status
create policy "inspections municipal read"
on inspections for select
using (public.current_app_role() = 'municipal');

create policy "inspections municipal update"
on inspections for update
using (public.current_app_role() = 'municipal')
with check (public.current_app_role() = 'municipal');

-- Arbiter: read all inspections (for dispute context)
create policy "inspections arbiter read"
on inspections for select
using (public.current_app_role() = 'arbiter');

-- Admin full
create policy "inspections admin full"
on inspections for all
using (public.is_admin())
with check (public.is_admin());


-- ======================== INSPECTION_ITEMS ========================

-- Inspector: manage items on own inspections
create policy "inspection_items inspector own"
on inspection_items for all
using (
    exists (
        select 1 from inspections i
        where i.id = inspection_items.inspection_id
          and i.inspector_id = auth.uid()
    )
)
with check (
    exists (
        select 1 from inspections i
        where i.id = inspection_items.inspection_id
          and i.inspector_id = auth.uid()
    )
);

-- GC: read items on own project inspections
create policy "inspection_items gc read"
on inspection_items for select
using (
    exists (
        select 1 from inspections i
        join projects p on p.id = i.project_id
        where i.id = inspection_items.inspection_id
          and p.gc_id = auth.uid()
    )
);

-- Municipal: read all
create policy "inspection_items municipal read"
on inspection_items for select
using (public.current_app_role() = 'municipal');

-- Admin full
create policy "inspection_items admin full"
on inspection_items for all
using (public.is_admin())
with check (public.is_admin());


-- ======================== DOCUMENTS ========================

-- Uploader can see own docs
create policy "documents uploader own"
on documents for select
using (uploaded_by = auth.uid());

-- GC: access docs on own projects
create policy "documents gc own project"
on documents for all
using (
    exists (
        select 1 from projects p
        where p.id = documents.project_id
          and p.gc_id = auth.uid()
    )
)
with check (
    exists (
        select 1 from projects p
        where p.id = documents.project_id
          and p.gc_id = auth.uid()
    )
);

-- Inspector: read docs on assigned inspections
create policy "documents inspector read"
on documents for select
using (
    exists (
        select 1 from inspections i
        where i.id = documents.inspection_id
          and i.inspector_id = auth.uid()
    )
);

-- Municipal: read all docs
create policy "documents municipal read"
on documents for select
using (public.current_app_role() = 'municipal');

-- Insert: anyone authenticated can upload, but must be self
create policy "documents insert own"
on documents for insert
with check (uploaded_by = auth.uid());

-- Admin full
create policy "documents admin full"
on documents for all
using (public.is_admin())
with check (public.is_admin());


-- ======================== DISPUTES ========================

-- Raiser can see own disputes
create policy "disputes raiser own"
on disputes for select
using (raised_by = auth.uid());

-- Assigned arbiter: full access
create policy "disputes arbiter assigned"
on disputes for all
using (assigned_arbiter = auth.uid())
with check (assigned_arbiter = auth.uid());

-- GC: read disputes on own projects
create policy "disputes gc read project"
on disputes for select
using (
    exists (
        select 1 from projects p
        where p.id = disputes.project_id
          and p.gc_id = auth.uid()
    )
);

-- Municipal: read all disputes
create policy "disputes municipal read"
on disputes for select
using (public.current_app_role() = 'municipal');

-- Arbiter role: read all disputes (for assignment)
create policy "disputes arbiter read all"
on disputes for select
using (public.current_app_role() = 'arbiter');

-- Insert: anyone authenticated, raised_by must be self
create policy "disputes insert own"
on disputes for insert
with check (raised_by = auth.uid());

-- Admin full
create policy "disputes admin full"
on disputes for all
using (public.is_admin())
with check (public.is_admin());


-- ======================== DISPUTE_COMMENTS ========================

-- Read comments on disputes you can see (leverages dispute policies)
create policy "dispute_comments read visible"
on dispute_comments for select
using (
    exists (
        select 1 from disputes d
        where d.id = dispute_comments.dispute_id
          and (
              d.raised_by = auth.uid()
              or d.assigned_arbiter = auth.uid()
              or public.current_app_role() in ('municipal', 'arbiter', 'admin')
              or exists (
                  select 1 from projects p
                  where p.id = d.project_id and p.gc_id = auth.uid()
              )
          )
    )
);

-- Insert: author must be self
create policy "dispute_comments insert own"
on dispute_comments for insert
with check (author_id = auth.uid());

-- Admin full
create policy "dispute_comments admin full"
on dispute_comments for all
using (public.is_admin())
with check (public.is_admin());


-- ======================== APPROVALS ========================

-- Municipal: full access (they issue approvals)
create policy "approvals municipal full"
on approvals for all
using (public.current_app_role() = 'municipal')
with check (public.current_app_role() = 'municipal');

-- GC: read approvals on own projects
create policy "approvals gc read project"
on approvals for select
using (
    exists (
        select 1 from projects p
        where p.id = approvals.project_id
          and p.gc_id = auth.uid()
    )
);

-- Inspector: read approvals on assigned inspections
create policy "approvals inspector read"
on approvals for select
using (
    exists (
        select 1 from inspections i
        where i.id = approvals.inspection_id
          and i.inspector_id = auth.uid()
    )
);

-- Admin full
create policy "approvals admin full"
on approvals for all
using (public.is_admin())
with check (public.is_admin());


-- ======================== NOTIFICATIONS ========================

-- Users only see their own notifications
create policy "notifications self only"
on notifications for select
using (user_id = auth.uid());

-- Users can mark their own as read
create policy "notifications self update"
on notifications for update
using (user_id = auth.uid())
with check (user_id = auth.uid());

-- System/admin can insert for any user
create policy "notifications admin insert"
on notifications for insert
with check (public.is_admin());

-- Admin full
create policy "notifications admin full"
on notifications for all
using (public.is_admin())
with check (public.is_admin());


-- ======================== AUDIT_LOG ========================

-- Append-only: service role inserts via backend
-- No user can delete or update audit_log entries
-- Admin can read all
create policy "audit_log admin read"
on audit_log for select
using (public.is_admin());

-- Users can read their own actions
create policy "audit_log self read"
on audit_log for select
using (actor_id = auth.uid());

-- No update or delete policies = immutable for RLS users


-- ======================== MERKLE_ANCHORS ========================

-- Read-only for authenticated users (public audit trail)
create policy "merkle_anchors authenticated read"
on merkle_anchors for select
using (auth.uid() is not null);

-- Only admin/service can insert
create policy "merkle_anchors admin insert"
on merkle_anchors for all
using (public.is_admin())
with check (public.is_admin());
