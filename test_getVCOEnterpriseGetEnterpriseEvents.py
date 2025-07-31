import unittest
import os
import time
from getVCOEnterpriseGetEnterpriseEvents import human_to_unixtime, load_config, create_session

class TestGetVCOEnterpriseGetEnterpriseEvents(unittest.TestCase):
    def test_human_to_unixtime(self):
        # Calculate expected values in local time
        expected_1970 = int(time.mktime(time.strptime("1970-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")))
        expected_2024 = int(time.mktime(time.strptime("2024-02-20 03:04:00", "%Y-%m-%d %H:%M:%S")))
        self.assertEqual(human_to_unixtime("1970-01-01 00:00:00"), expected_1970)
        self.assertEqual(human_to_unixtime("2024-02-20 03:04:00"), expected_2024)

    def test_load_config_defaults(self):
        # Use a minimal config file
        # Input times are interpreted as local time; unix time is always seconds since 1970-01-01 00:00:00 UTC
        config_path = "test_config.jsonc"
        with open(config_path, "w") as f:
            f.write('''{
                "limit_event": 123,
                "start_human": "2024-02-20 03:04:00",
                "stop_human": "2025-02-22 15:04:00",
                "VCO": "test-vco",
                "AUTHTOKEN": "token",
                "basepath": "/api/",
                "enterpriseId": 42,
                "ssl_verify": false
            }''')
        os.environ.pop('ENTERPRISEID', None)
        config = load_config(config_path)
        self.assertEqual(config['limit_event'], 123)
        self.assertEqual(config['start_human'], "2024-02-20 03:04:00")
        self.assertEqual(config['stop_human'], "2025-02-22 15:04:00")
        self.assertEqual(config['enterpriseId'], 42)
        import time
        # Input is local time; unix time is seconds since 1970-01-01 00:00:00 UTC
        expected_start = int(time.mktime(time.strptime("2024-02-20 03:04:00", "%Y-%m-%d %H:%M:%S"))) * 1000
        expected_stop = int(time.mktime(time.strptime("2025-02-22 15:04:00", "%Y-%m-%d %H:%M:%S"))) * 1000
        self.assertEqual(config['start'], expected_start)
        self.assertEqual(config['stop'], expected_stop)
        os.remove(config_path)

    def test_create_session(self):
        params = {'AuthH': 'Token test', 'verify': False}
        session = create_session(params)
        self.assertEqual(session.headers['Authorization'], 'Token test')
        self.assertFalse(session.verify)

    def test_cli_overrides_config(self):
        # Simulate CLI args
        class Args:
            start_human = "2099-01-01 00:00:00"
            stop_human = "2099-12-31 23:59:59"
        config_path = "test_config.jsonc"
        with open(config_path, "w") as f:
            f.write('''{
                "limit_event": 123,
                "start_human": "2024-02-20 03:04:00",
                "stop_human": "2025-02-22 15:04:00",
                "VCO": "test-vco",
                "AUTHTOKEN": "token",
                "basepath": "/api/",
                "enterpriseId": 42,
                "ssl_verify": false
            }''')
        config = load_config(config_path, cli_args=Args)
        self.assertEqual(config['start_human'], "2099-01-01 00:00:00")
        self.assertEqual(config['stop_human'], "2099-12-31 23:59:59")
        os.remove(config_path)

    def test_argparse_help(self):
        import subprocess, sys
        result = subprocess.run([sys.executable, 'getVCOEnterpriseGetEnterpriseEvents.py', '--help'], capture_output=True, text=True)
        self.assertIn('usage:', result.stdout)
        self.assertIn('--start_human', result.stdout)
        self.assertIn('--stop_human', result.stdout)

if __name__ == "__main__":
    unittest.main()
