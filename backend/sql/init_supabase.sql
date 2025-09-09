create extension if not exists vector;

create table if not exists public.face_templates (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  embedding vector(512) not null,
  quality_score real,
  created_at timestamptz default now()
);

create index if not exists face_templates_embedding_cos
  on public.face_templates using ivfflat (embedding vector_cosine_ops) with (lists = 100);

alter table public.face_templates enable row level security;

create policy "select own" on public.face_templates
for select using (auth.uid() = user_id);

create policy "insert own" on public.face_templates
for insert with check (auth.uid() = user_id);
