-- New function, does not touch the existing match_chunks (teammates depend on it).
-- Adds: min_similarity cutoff, document_id, page_start, page_end, section, metadata.
create or replace function match_chunks_v2(
    query_embedding vector(384),
    match_count int default 5,
    match_lab_id text default null,
    min_similarity float default 0.0
)
returns table (
    id bigint,
    document_id bigint,
    content text,
    section text,
    page_start int,
    page_end int,
    metadata jsonb,
    similarity float
)
language sql
stable
as $$
    select
        c.id,
        c.document_id,
        c.content,
        c.section,
        c.page_start,
        c.page_end,
        c.metadata,
        1 - (c.embedding <=> query_embedding) as similarity
    from chunks c
    where (match_lab_id is null or c.lab_id = match_lab_id)
      and 1 - (c.embedding <=> query_embedding) >= min_similarity
    order by c.embedding <=> query_embedding asc
    limit match_count;
$$;
