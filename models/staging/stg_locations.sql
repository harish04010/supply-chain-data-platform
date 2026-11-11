select location_id, location_type, region from read_csv('{{ var("raw_path") }}/locations.csv', header = true, all_varchar = true)
