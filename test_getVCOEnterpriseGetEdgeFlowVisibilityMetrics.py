import unittest
import os
from getVCOEnterpriseGetEdgeFlowVisibilityMetrics import human_to_rfc3339_nano, load_config, create_session

class TestGetVCOEnterpriseGetEdgeFlowVisibilityMetrics(unittest.TestCase):
    def test_human_to_rfc3339_nano(self):
        # Test with default local timezone
        result = human_to_rfc3339_nano("1970-01-01 00:00:00")
        self.assertTrue(result.startswith("1970-01-01T00:00:00.000000000"))
        # Test with explicit timezone offset (e.g. UTC+0)
        result = human_to_rfc3339_nano("2024-02-20 03:04:00", tz_offset_min=0)
        self.assertEqual(result, "2024-02-20T03:04:00.000000000+00:00")
        # Test with explicit timezone offset (e.g. UTC+2)
        result = human_to_rfc3339_nano("2024-02-20 03:04:00", tz_offset_min=120)
        self.assertEqual(result, "2024-02-20T03:04:00.000000000+02:00")

    def test_load_config_defaults(self):
        config_path = "test_config.jsonc"
        with open(config_path, "w") as f:
            f.write('''{
                "limit_flow": 123,
                "start_human": "2024-02-20 03:04:00",
                "stop_human": "2025-02-22 15:04:00",
                "VCO": "test-vco",
                "AUTHTOKEN": "token",
                "basepath": "/api/",
                "EdgeID": 99,
                "enterpriseId": 42,
                "ssl_verify": false
            }''')
        os.environ.pop('ENTERPRISEID', None)
        config = load_config(config_path)
        self.assertEqual(config['limit_flow'], 123)
        self.assertEqual(config['start_human'], "2024-02-20 03:04:00")
        self.assertEqual(config['stop_human'], "2025-02-22 15:04:00")
        self.assertEqual(config['EdgeID'], 99)
        self.assertEqual(config['enterpriseId'], 42)
        self.assertTrue(config['start'].startswith("2024-02-20T03:04:00.000000000"))
        self.assertTrue(config['stop'].startswith("2025-02-22T15:04:00.000000000"))
        os.remove(config_path)

    def test_create_session(self):
        params = {'AuthH': 'Token test', 'verify': False}
        session = create_session(params)
        self.assertEqual(session.headers['Authorization'], 'Token test')
        self.assertFalse(session.verify)

if __name__ == "__main__":
    unittest.main()
