-- Warns rather than fails: staging already deduplicates, but the upstream team needs to know.
{{ config(severity = 'warn') }}
select * from {{ ref('audit_snapshot_duplicates') }}
