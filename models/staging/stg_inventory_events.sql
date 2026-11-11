-- The event stream delivers duplicates and late, out-of-order events.
-- Deduplicate on event_id (keep the first delivery) and use event time, not ingestion time.
select event_id, event_ts::timestamp as event_ts, event_ts::timestamp::date as event_date,
       ingested_ts::timestamp as ingested_ts, location_id, sku, event_type, quantity::int as quantity,
       datediff('hour', event_ts::timestamp, ingested_ts::timestamp) as ingestion_lag_hours
from read_json('{{ var("raw_path") }}/inventory_events.jsonl', format = 'newline_delimited', columns = {
    event_id: 'VARCHAR', event_ts: 'VARCHAR', ingested_ts: 'VARCHAR', location_id: 'VARCHAR',
    sku: 'VARCHAR', event_type: 'VARCHAR', quantity: 'INTEGER'})
qualify row_number() over (partition by event_id order by ingested_ts) = 1
