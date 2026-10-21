-- ============================================================================
-- Performance indexes
-- ============================================================================

-- profiles
create index if not exists idx_profiles_company on profiles(company_id);
create index if not exists idx_profiles_role on profiles(role);

-- projects
create index if not exists idx_projects_gc on projects(gc_id);
create index if not exists idx_projects_company on projects(company_id);
create index if not exists idx_projects_status on projects(status);

-- project_members
create index if not exists idx_project_members_user on project_members(user_id);
create index if not exists idx_project_members_project on project_members(project_id);

-- permits
create index if not exists idx_permits_project on permits(project_id);
create index if not exists idx_permits_status on permits(status);
create index if not exists idx_permits_issued_by on permits(issued_by);

-- inspections
create index if not exists idx_inspections_project on inspections(project_id);
create index if not exists idx_inspections_inspector on inspections(inspector_id);
create index if not exists idx_inspections_permit on inspections(permit_id);
create index if not exists idx_inspections_status on inspections(status);
create index if not exists idx_inspections_scheduled on inspections(scheduled_at);

-- inspection_items
create index if not exists idx_inspection_items_inspection on inspection_items(inspection_id);

-- documents
create index if not exists idx_documents_project on documents(project_id);
create index if not exists idx_documents_inspection on documents(inspection_id);
create index if not exists idx_documents_uploaded_by on documents(uploaded_by);

-- disputes
create index if not exists idx_disputes_project on disputes(project_id);
create index if not exists idx_disputes_raised_by on disputes(raised_by);
create index if not exists idx_disputes_arbiter on disputes(assigned_arbiter);
create index if not exists idx_disputes_status on disputes(status);

-- dispute_comments
create index if not exists idx_dispute_comments_dispute on dispute_comments(dispute_id);

-- approvals
create index if not exists idx_approvals_project on approvals(project_id);
create index if not exists idx_approvals_status on approvals(status);

-- notifications
create index if not exists idx_notifications_user on notifications(user_id);
create index if not exists idx_notifications_unread on notifications(user_id) where read = false;

-- audit_log
create index if not exists idx_audit_log_actor on audit_log(actor_id);
create index if not exists idx_audit_log_table on audit_log(table_name);
create index if not exists idx_audit_log_record on audit_log(record_id);
create index if not exists idx_audit_log_created on audit_log(created_at desc);

-- merkle_anchors
create index if not exists idx_merkle_anchors_date on merkle_anchors(anchor_date desc);
create index if not exists idx_merkle_anchors_source on merkle_anchors(source_table);
