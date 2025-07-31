#!/usr/bin/env python3
# Fetch all Velocloud VCO Enterprise Events, handling pagination and saving to JSON.
# Designed for robust, memory-efficient log collection from the Velocloud API.

# --- Standard library imports ---
from time import sleep
import requests
import json
import string
import random
import time
import os
import logging
from datetime import datetime
# pip install jsoncomment
from jsoncomment import JsonComment
from multiprocessing import Process, Queue
import sys
import warnings
from urllib3.exceptions import InsecureRequestWarning
import argparse

# Only show InsecureRequestWarning once if SSL verification is disabled
warnings.simplefilter("once", InsecureRequestWarning)

# --- Utility functions ---
def human_to_unixtime(human_time, time_format="%Y-%m-%d %H:%M:%S"):
    """
    Convert a human-readable time string to Unix time (seconds since epoch).

    Note:
        - The returned Unix time is the number of seconds since 1970-01-01 00:00:00 *local time* (not UTC).
        - This is system-dependent: the result will differ depending on the system's timezone and daylight saving time (DST) settings.
        - Example: On a system set to UTC+1, '2020-02-29 12:00:00' will be interpreted as 12:00 in UTC+1, not UTC.
    """
    if 'logger' in globals():   # to pass unit tests
        logger.info(f"[human_to_unixtime] input: human_time={human_time}, time_format={time_format}")
    dt = datetime.strptime(human_time, time_format)
    unix_time = int(time.mktime(dt.timetuple()))
    if 'logger' in globals():   # to pass unit tests
        logger.info(f"[human_to_unixtime] output: {unix_time}")
    return unix_time

def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch Velocloud VCO Enterprise Events with flexible time range and config overrides."
    )
    parser.add_argument('--start_human', type=str, help='Start time (human-readable, e.g. "2024-02-20 03:04:00")')
    parser.add_argument('--stop_human', type=str, help='Stop time (human-readable, e.g. "2025-02-22 15:04:00")')
    # Add more arguments here as needed
    return parser.parse_args()

# --- Configuration loading ---
def load_config(config_file, cli_args=None):
    """
    Load configuration from JSONC file, environment variables, and command line arguments.
    Priority: command line > environment > config file > default.
    Exits if required parameters are missing.
    """
    parser = JsonComment(json)
    try:
        with open(config_file, 'r') as file:
            config = parser.load(file)
    except Exception as e:
        logging.error(f"Failed to load config file '{config_file}': {e}")
        sys.exit(1)
    config['limit_event'] = int(os.getenv('LIMIT_EVENT', config.get('limit_event', 2048)))
    # Priority: CLI > ENV > config > default
    start_human = (cli_args.start_human if cli_args and cli_args.start_human else
                   os.getenv('START_HUMAN', config.get('start_human', "2024-02-20 03:04:00")))
    stop_human = (cli_args.stop_human if cli_args and cli_args.stop_human else
                  os.getenv('STOP_HUMAN', config.get('stop_human', "2025-02-22 15:04:00")))
    config['start_human'] = start_human
    config['stop_human'] = stop_human
    config['VCO'] = os.getenv('VCO', config.get('VCO', "vco99-us.velocloud.net"))
    config['AUTHTOKEN'] = os.getenv('AUTHTOKEN', config.get('AUTHTOKEN', "your_default_token"))
    config['basepath'] = os.getenv('BASEPATH', config.get('basepath', "/portal/rest/"))
    config['log_level'] = os.getenv('LOG_LEVEL', config.get('log_level', 'INFO')).upper()
    # Require enterpriseId, no default
    enterprise_id = os.getenv('ENTERPRISEID', config.get('enterpriseId'))
    if enterprise_id is None:
        logging.error("Missing required 'enterpriseId' in config.jsonc or environment.")
        sys.exit(1)
    config['enterpriseId'] = int(enterprise_id)
    config['ssl_verify'] = os.getenv('SSL_VERIFY', str(config.get('ssl_verify', 'True'))).lower() in ('1', 'true', 'yes')
    # Convert human times to unix ms here
    config['start'] = human_to_unixtime(config['start_human']) * 1000
    config['stop'] = human_to_unixtime(config['stop_human']) * 1000
    return config

# --- Session creation ---
def create_session(session_params):
    """
    Create a requests.Session with authentication and SSL settings.
    """
    session = requests.Session()
    session.headers.update({'Authorization': session_params['AuthH']})
    session.verify = session_params['verify']
    session.headers.update({'Connection': 'keep-alive'})
    return session

# --- Worker process for fetching data ---
def fetch_data_worker(queue, session_params, url, enterpriseId, start, stop, Vtype, limit_event, logger):
    """
    Worker process: fetches paginated event data from the API and puts it on the queue.
    Handles pagination, error logging, and queue signaling.
    """
    session = create_session(session_params)
    first_page = True
    while True:
        # Build request body for first or subsequent pages
        if first_page:
            # First page: include filter and interval
            body = {
                "filter": {
                    "limit": limit_event
                },
                "interval": {
                    "start": start,
                    "end": stop,
                    "type": Vtype
                },
                "enterpriseId": enterpriseId
            }
        else:
            # Next pages: use nextPageLink from previous response
            body = {
                "nextPageLink": data["metaData"]["nextPageLink"],
                "limit": limit_event,
                "interval": {
                    "start": start,
                    "end": stop,
                    "type": Vtype
                },
                "enterpriseId": enterpriseId
            }
        json_body = json.dumps(body)
        # Log request and handle errors
        logger.info(f"fetch_data_worker: Start new request")
        logger.debug(f"fetch_data_worker: Request body: {json_body}")
        start_time = datetime.now()
        try:
            response = session.post(url, data=json_body)
        except requests.exceptions.RequestException as e:
            logger.error(f"fetch_data_worker: Request failed: {e}")
            queue.put(None)
            break
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        size_bytes = len(response.content) if 'response' in locals() else 0
        speed_mbps = (size_bytes * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0
        logger.info(f"fetch_data_worker: POST transfer {size_bytes} bytes in {elapsed:.3f} s, speed: {speed_mbps:.3f} Mbps")
        if 'response' not in locals() or response.status_code != 200:
            logger.error(f"fetch_data_worker: Error {getattr(response, 'status_code', 'N/A')}, queue size before put(None): {queue.qsize()}")
            logger.error(f"fetch_data_worker: Response text: {getattr(response, 'text', 'No response')}")
            queue.put(None)
            break
        # Parse and validate response
        data = None
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}, response text: {response.text}")
            queue.put(None)
            break
        if not data or 'data' not in data:
            logger.error(f"fetch_data_worker: No data in response, queue size before put(None): {queue.qsize()}. Response data: {response.text} please ask Velocloud (again) to return http 401 for invalid token instead http 200")
            queue.put(None)
            break
        # Put data on queue for main process
        logger.info(f"fetch_data_worker: Received {len(data['data'])} items, queue size before put: {queue.qsize()}")
        if len(data['data']) == 0:
            logger.info(f"fetch_data_worker: No data, is empty(0), response was: {response.text}")
        if len(data['data']) == 1:
            logger.info(f"fetch_data_worker: No data, is empty(1), response was: {response.text}")
        logger.info(f"fetch_data_worker: Putting chunk of {len(data['data'])} items to queue. Queue size before put: {queue.qsize()}")
        queue.put(data["data"])
        logger.info(f"fetch_data_worker: Queue size after put: {queue.qsize()}")
        first_page = False
        # Check for more pages, else signal end
        if 'metaData' not in data or 'more' not in data["metaData"] or not data["metaData"]["more"]:
            logger.info(f"fetch_data_worker: No more pages, queue size before put(None): {queue.qsize()}")
            queue.put(None)
            break

# --- Logging setup ---
def setup_logging(log_level):
    """
    Configure logging to both console and file, with timestamps and levels.
    """
    LOG_FILENAME = f"enterprise_events_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILENAME)
        ]
    )
    return logging.getLogger(__name__)

# --- JSON writing helper ---
def write_json_with_indent(item, output_file, indent=4):
    """
    Write a JSON item to file, indented and pretty-printed for readability.
    """
    json_str = json.dumps(item, indent=indent)
    indented_json_str = "\n".join(" " * indent + line for line in json_str.splitlines())
    output_file.write(indented_json_str)

# --- Main process ---
def main():
    """
    Main process: loads config, sets up logging, starts worker, and writes data to file.
    Handles queue communication and progress logging.
    """
    global logger
    logger = setup_logging(logging.INFO)    # Initial logger, which is also available in load_config
    # Parse command line arguments
    cli_args = parse_args()
    # Load configuration and initialize logging
    config = load_config('config.jsonc', cli_args=cli_args)
    log_level = getattr(logging, config['log_level'], logging.INFO)
    # Reconfigure logger with the specified log level
    logger = setup_logging(log_level)
    Vtype = "past12Months"  # This parameter was happily 'reverse engineered' in Europe
    # Prepare API URL and output filename
    url = "https://" + config['VCO'] + config['basepath'] + "/event/getEnterpriseEvents"
    output_filename = f"output-EnterpriseEvents_{config['start_human'].replace(':', '-').replace(' ', '_')}_to_{config['stop_human'].replace(':', '-').replace(' ', '_')}.json"
    session_params = {
        'AuthH': "Token " + config['AUTHTOKEN'],
        'verify': config['ssl_verify']
    }
    # Start worker process for fetching data
    queue = Queue(maxsize=4)
    fetcher = Process(target=fetch_data_worker, args=(queue, session_params, url, config['enterpriseId'], config['start'], config['stop'], Vtype, config['limit_event'], logger))
    fetcher.start()
    # Write data chunks to output file as they arrive
    with open(output_filename, 'w') as output_file:
        output_file.write("[\n")
        FirstElement = True
        indent = 4
        while True:
            logger.info(f"main: Waiting for data from queue. Current queue size: {queue.qsize()}")
            data_chunk = queue.get()
            logger.info(f"main: Got data from queue. Current queue size after get: {queue.qsize()} - items: {len(data_chunk) if data_chunk else 'None'}")
            if data_chunk is None:
                logger.info("main: Received None from queue, ending write loop.")
                break
            process_start = datetime.now()
            for item in data_chunk:
                if not FirstElement:
                    output_file.write(",\n")
                else:
                    FirstElement = False
                write_json_with_indent(item, output_file, indent=indent)
            process_end = datetime.now()
            process_elapsed = (process_end - process_start).total_seconds()
            chunk_size = sum(len(json.dumps(item)) for item in data_chunk) if data_chunk else 0
            process_speed_mbps = (chunk_size * 8) / (process_elapsed * 1_000_000) if process_elapsed > 0 else 0
            logger.info(f"main: Wrote chunk of {len(data_chunk)} items, {chunk_size} bytes in {process_elapsed:.3f} s, speed: {process_speed_mbps:.3f} Mbps")
        output_file.write("\n]")
    fetcher.join()
    logger.info(f"main: Data has been written to '{output_filename}'")

if __name__ == "__main__":
    main()





