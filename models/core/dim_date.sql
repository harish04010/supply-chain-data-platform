select d::date as date_day, date_trunc('week', d)::date as week_start, strftime(d, '%Y-%m') as month,
       dayofweek(d) as day_of_week, dayofweek(d) in (0, 6) as is_weekend
from range(date '2026-02-01', date '2026-08-15', interval 1 day) t(d)
