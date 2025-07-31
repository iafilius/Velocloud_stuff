import unittest
import os
import tempfile
import json
from getVCOEnterpriseGetEnterpriseEvents import human_to_unixtime, load_config, create_session, write_json_with_indent

class TestGetVCOEnterpriseGetEnterpriseEventsExtra(unittest.TestCase):
    def test_human_to_unixtime_invalid(self):
        with self.assertRaises(ValueError):
            human_to_unixtime("not-a-date")

    def test_human_to_unixtime_leap(self):
        # Leap year: 2020-02-29 12:00:00 local time
        # This test works in any system timezone by comparing to the expected value for local time
        import time
        from datetime import datetime
        dt = datetime.strptime("2020-02-29 12:00:00", "%Y-%m-%d %H:%M:%S")
        expected = int(time.mktime(dt.timetuple()))
        self.assertEqual(human_to_unixtime("2020-02-29 12:00:00"), expected)

    def test_load_config_missing_enterpriseid(self):
        config_path = "test_config_missing.jsonc"
        with open(config_path, "w") as f:
            f.write('''{
                "limit_event": 1,
                "start_human": "2024-02-20 03:04:00",
                "stop_human": "2025-02-22 15:04:00"
            }''')
        # Remove env var if set
        os.environ.pop('ENTERPRISEID', None)
        # Should exit(1) due to missing enterpriseId
        with self.assertRaises(SystemExit):
            load_config(config_path)
        os.remove(config_path)

    def test_load_config_env_override(self):
        config_path = "test_config_env.jsonc"
        with open(config_path, "w") as f:
            f.write('''{
                "limit_event": 1,
                "start_human": "2024-02-20 03:04:00",
                "stop_human": "2025-02-22 15:04:00",
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
