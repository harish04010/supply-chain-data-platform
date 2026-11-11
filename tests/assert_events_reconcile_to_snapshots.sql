-- Fails if the event stream and the WMS snapshots disagree on any day's inventory change.
select * from {{ ref('recon_events_vs_snapshots') }}
