create table if not exists public.learner_memories (
  user_id text primary key,
  memory jsonb not null default '{}'::jsonb,
  version integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint learner_memories_user_id_not_empty check (char_length(trim(user_id)) > 0)
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists learner_memories_set_updated_at on public.learner_memories;
create trigger learner_memories_set_updated_at
before update on public.learner_memories
for each row execute function public.set_updated_at();

alter table public.learner_memories enable row level security;
