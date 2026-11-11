-- One row per PO line with what the vendor said it shipped (ASN) and what the DC received.
select p.po_number, p.po_line, p.vendor_id, p.sku, p.dc_id, p.order_date, p.promised_date, p.ordered_qty, p.unit_cost,
       a.shipped_qty as asn_qty, r.received_qty, r.receipt_date,
       r.receipt_date is not null as is_received,
       case when r.receipt_date is not null then datediff('day', p.promised_date, r.receipt_date) end as days_late,
       r.receipt_date <= p.promised_date as is_on_time,
       r.received_qty >= p.ordered_qty as is_in_full,
       (r.receipt_date <= p.promised_date) and (r.received_qty >= p.ordered_qty) as is_otif,
       a.shipped_qty is distinct from r.received_qty and r.receipt_date is not null as asn_mismatch
from {{ ref('stg_purchase_orders') }} p
left join {{ ref('stg_asn') }} a using (po_number, sku)
left join {{ ref('stg_dc_receipts') }} r using (po_number, sku)
