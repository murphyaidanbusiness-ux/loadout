create table profiles (id uuid primary key references auth.users, role text default 'owner', is_pro boolean default false);
create table slots (id uuid primary key default gen_random_uuid(), walker_id uuid references profiles, walker_name text,
  starts_at timestamptz, booked_by uuid references profiles);
alter table profiles enable row level security;
alter table slots enable row level security;
create policy "read slots" on slots for select using (true);
