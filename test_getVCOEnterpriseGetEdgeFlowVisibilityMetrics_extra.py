import unittest
import os
import tempfile
from getVCOEnterpriseGetEdgeFlowVisibilityMetrics import human_to_rfc3339_nano, load_config, create_session, write_json_with_indent

class TestGetVCOEnterpriseGetEdgeFlowVisibilityMetricsExtra(unittest.TestCase):
    def test_human_to_rfc3339_nano_invalid(self):
        with self.assertRaises(ValueError):
            human_to_rfc3339_nano("not-a-date")

    def test_human_to_rfc3339_nano_tz(self):
        # Test with explicit negative offset (UTC-2)
        result = human_to_rfc3339_nano("2024-02-20 03:04:00", tz_offset_min=-120)
        self.assertEqual(result, "2024-02-20T03:04:00.000000000-02:00")
        # Test with explicit positive offset (UTC+5:30)
        result = human_to_rfc3339_nano("2024-02-20 03:04:00", tz_offset_min=330)
        self.assertEqual(result, "2024-02-20T03:04:00.000000000+05:30")

    def test_load_config_missing_enterpriseid(self):
        config_path = "test_config_missing.jsonc"
        with open(config_path, "w") as f:
            f.write('''{
                "limit_flow": 1,
                "start_human": "2024-02-20 03:04:00",
                "stop_human": "2025-02-22 15:04:00",
                "EdgeID": 1
            }''')
        os.environ.pop('ENTERPRISEID', None)
        with self.assertRaises(SystemExit):
            load_config(config_path)
        os.remove(config_path)

    def test_load_config_env_override(self):
        config_path = "test_config_env.jsonc"
        with open(config_path, "w") as f:
            f.write('''{
                "limit_flow": 1,
                "start_human": "2024-02-20 03:04:00",
                "stop_human": "2025-02-22 15:04:00",
                "EdgeID": 1,
                "enterpriseId": 42
            }''')
        os.environ['ENTERPRISEID'] = '99'
        config = load_config(config_path)
        self.assertEqual(config['enterpriseId'], 99)
        os.environ.pop('ENTERPRISEID', None)
        os.remove(config_path)

    def test_create_session_headers(self):
        params = {'AuthH': 'Token test', 'verify': True}
        session = create_session(params)
        self.assertEqual(session.headers['Authorization'], 'Token test')
        self.assertTrue(session.verify)

    def test_write_json_with_indent(self):
        data = {"a": 1, "b": [2, 3]}
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
            write_json_with_indent(data, tmp, indent=2)
            tmp_path = tmp.name
        with open(tmp_path) as f:
            content = f.read()
        self.assertIn('  "a": 1', content)
        self.assertIn('  "b": [', content)
        os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
