-- ============================================================================
-- Helper functions for RLS policies
-- ============================================================================

-- Get the current user's app role from profiles
create or replace function public.current_app_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
    select role
    from public.profiles
    where id = auth.uid()
$$;

-- Get the current user's company_id from profiles
create or replace function public.current_company_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
    select company_id
    from public.profiles
    where id = auth.uid()
$$;

-- Check if current user is admin
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.profiles
        where id = auth.uid()
          and role = 'admin'
    )
$$;

-- Check if current user is a member of a given project
create or replace function public.is_project_member(p_project_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.project_members
        where project_id = p_project_id
          and user_id = auth.uid()
    )
$$;
