INSERT INTO organizations (id, name, type, is_active)
VALUES
    ('10000000-0000-0000-0000-000000000001', 'Demo Retailer', 'RETAILER', true),
    ('20000000-0000-0000-0000-000000000001', 'Demo Manufacturer', 'MANUFACTURER', true)
ON CONFLICT (id) DO NOTHING;
