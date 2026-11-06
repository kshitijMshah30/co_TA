-- Proposed logging table for /ask requests. Not yet applied — needs sign-off.
create table if not exists query_logs (
    id bigserial primary key,
    lab_id text not null,
    question text not null,
    answer text not null,
    retrieved_chunk_ids bigint[] not null default '{}',
    similarities float[] not null default '{}',
    below_threshold boolean not null default false,
    llm_backend text not null,
    created_at timestamptz not null default now()
);

create index if not exists query_logs_lab_id_idx on query_logs (lab_id);
create index if not exists query_logs_created_at_idx on query_logs (created_at);
