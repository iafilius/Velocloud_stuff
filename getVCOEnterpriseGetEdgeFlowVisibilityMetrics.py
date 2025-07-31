#!/usr/bin/env python3
# Fetch all Velocloud VCO Edge Flow Visibility Metrics, handling pagination and saving to JSON.
# Designed for robust, memory-efficient log collection from the Velocloud API.

# --- Standard library and third-party imports ---
from time import sleep
import requests
import json
import string
import random
import sys
import os
from datetime import datetime, timezone, timedelta
from jsoncomment import JsonComment
from multiprocessing import Process, Queue
import logging
import warnings
from urllib3.exceptions import InsecureRequestWarning
import time
import argparse

# Only show InsecureRequestWarning once if SSL verification is disabled
warnings.simplefilter("once", InsecureRequestWarning)

# --- Helper functions ---
def human_to_rfc3339_nano(human_time, time_format="%Y-%m-%d %H:%M:%S", tz_offset_min=None):
    if 'logger' in globals():   # to pass unit tests
        logger.info(f"[human_to_rfc3339_nano] input: human_time={human_time}, time_format={time_format}, tz_offset_min={tz_offset_min}")
    dt = datetime.strptime(human_time, time_format)
    if tz_offset_min is None:
        # Use local timezone offset
        offset_sec = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
        tz = timezone(timedelta(seconds=offset_sec))
    else:
        tz = timezone(timedelta(minutes=tz_offset_min))
    dt = dt.replace(tzinfo=tz)
    # Format to RFC3339 with nanosecond precision and correct timezone
    base = dt.strftime('%Y-%m-%dT%H:%M:%S')
    nanos = '.000000000'  # always 9 digits, as we have no real nanosecond info
    offset = dt.strftime('%z')  # e.g. +0200
    if offset:
        offset = offset[:3] + ':' + offset[3:]
    else:
        offset = '+00:00'
    rfc3339 = f"{base}{nanos}{offset}"
    if 'logger' in globals():   # to pass unit tests
        logger.info(f"[human_to_rfc3339_nano] output: {rfc3339}")
    return rfc3339

def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch Velocloud VCO Edge Flow Visibility Metrics with flexible time range and config overrides."
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
    config['limit_flow'] = int(os.getenv('LIMIT_FLOW', config.get('limit_flow', 204800)))
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
    config['EdgeID'] = int(os.getenv('EDGEID', config.get('EdgeID', 12345)))
    config['log_level'] = os.getenv('LOG_LEVEL', config.get('LOG_LEVEL', 'INFO')).upper()
    # Require enterpriseId, no default
    enterprise_id = os.getenv('ENTERPRISEID', config.get('enterpriseId'))
    if enterprise_id is None:
        logging.error("Missing required 'enterpriseId' in config.jsonc or environment.")
        sys.exit(1)
    config['enterpriseId'] = int(enterprise_id)
    config['ssl_verify'] = os.getenv('SSL_VERIFY', str(config.get('ssl_verify', 'True'))).lower() in ('1', 'true', 'yes')
    # Convert human times to RFC3339/ISO8601 with nanosecond precision
    config['start'] = human_to_rfc3339_nano(config['start_human'])
    config['stop'] = human_to_rfc3339_nano(config['stop_human'])
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
def fetch_data_worker(queue, session_params, url, EdgeID, enterpriseId, start, stop, limit_flow):
    """
    Worker process: fetches paginated flow data from the API and puts it on the queue.
    Handles pagination, error logging, and queue signaling.
    """
    # Create a session for this process
    session = create_session(session_params)
    first_page = True
    while True:
        # Build request body for first or subsequent pages
        if first_page:
            # First page: include all required fields
            body = {
                "edgeId": EdgeID,
                "enterpriseId": enterpriseId,
                "interval": {"start": start, "end": stop},
                "limit": limit_flow,
                "_filterSpec": False
            }
        else:
            # Next pages: use nextPageLink from previous response
            body = {
                "edgeId": EdgeID,
                "interval": {"start": start, "end": stop},
                "nextPageLink": data["metaData"]["nextPageLink"]
            }
        json_body = json.dumps(body)
        # Log request and handle errors
        if first_page:
            logger.info(f"fetch_data_worker: Start new request with page limit: {limit_flow}")
        else:
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
        size_bytes = len(response.content)
        speed_mbps = (size_bytes * 8) / (elapsed * 1_000_000) if elapsed > 0 else 0
        logger.info(f"fetch_data_worker: POST transfer {size_bytes} bytes in {elapsed:.3f} s, speed: {speed_mbps:.3f} Mbps")
        if response.status_code != 200:
            logger.error(f"fetch_data_worker: Error {response.status_code}, queue size before put(None): {queue.qsize()}")
            logger.error(f"fetch_data_worker: Response text: {response.text}")
            queue.put(None)
            break
        # Extract data from response, and quit when (no longer) found
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
        # Special handling for 'other' summary element
        if len(data['data']) == 0:
            logger.info(f"fetch_data_worker: No data, is empty(0), response was: {response.text}")
        # Experience shows Velo can't count, and keeps repeating this 'other' element multiple times (not a bug, but a feature)
        if len(data['data']) == 1 and data['data'][0].get("name") == "other":
            # Skip to send data, when only contains the summary element with name "other"
            logger.info(f"fetch_data_worker: No data, only status page, not putting this on queue (please velo stop this)")
            logger.debug(f"fetch_data_worker: response was: {response.text}")
            # Don't break here, below we will check if more data is expected
        else:
            # Main payload is not empty, so put it on the queue
            logger.info(f"fetch_data_worker: Putting chunk of {len(data['data'])} items to queue. Queue size before put: {queue.qsize()}")
            queue.put(data["data"])
            logger.info(f"fetch_data_worker: Queue size after put: {queue.qsize()}")
            first_page = False
        # Check for more pages, else signal end
        if 'metaData' not in data or 'more' not in data["metaData"] or not data["metaData"]["more"]:
            logger.info(f"fetch_data_worker: No more pages, queue size before put(None): {queue.qsize()}")
            queue.put(None)
            break

# --- JSON writing helper ---
def write_json_with_indent(item, output_file, indent=4):
    """
    Write a JSON item to file, indented and pretty-printed for readability.
    """
    json_str = json.dumps(item, indent=indent)
    indented_json_str = "\n".join(" " * indent + line for line in json_str.splitlines())
    output_file.write(indented_json_str)

# --- Logging setup ---
def setup_logging(log_level):
    """
    Configure logging to both console and file, with timestamps and levels.
    """
    LOG_FILENAME = f'edgeflow_metrics_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
    logging.basicConfig(
        level=log_level,  # Log level from config
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILENAME)
        ]
    )
    return logging.getLogger(__name__)

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
    config = load_config("config.jsonc", cli_args=cli_args)
    log_level = getattr(logging, config['log_level'], logging.INFO)
    # Reconfigure logger with the specified log level
    logger = setup_logging(log_level)
    url = "https://" + config['VCO'] + config['basepath'] + "metrics/getEdgeFlowVisibilityMetrics"
    session_params = {
        'AuthH': "Token " + config['AUTHTOKEN'],
        'verify': config['ssl_verify']
    }
    # Start worker process for fetching data
    queue = Queue(maxsize=4)
    fetcher = Process(target=fetch_data_worker, args=(queue, session_params, url, config['EdgeID'], config['enterpriseId'], config['start'], config['stop'], config['limit_flow']))
    fetcher.start()
    # Write data chunks to output file as they arrive
    output_filename = f"output-EdgeFlowVisibilityMetrics_{config['start_human'].replace(':', '-').replace(' ', '_')}_to_{config['stop_human'].replace(':', '-').replace(' ', '_')}.json"
    with open(output_filename, 'w') as output_file:
        output_file.write("[\n")
        FirstElement = True
        while True:
            logger.info(f"main: Waiting for data from queue. Current queue size: {queue.qsize()}")
            data_chunk = queue.get()
            logger.info(f"main: Got data from queue. Current queue size after get: {queue.qsize()} - items: {len(data_chunk) if data_chunk else 'None'}")
            if data_chunk is None:
                logger.info("main: Received None from queue, ending write loop.")
                break
            process_start = datetime.now()
            for item in data_chunk:
                if item.get("name") == "other":
                    continue
                if not FirstElement:
                    output_file.write(",\n")
                else:
                    FirstElement = False
                write_json_with_indent(item, output_file, indent=4)
            process_end = datetime.now()
            process_elapsed = (process_end - process_start).total_seconds()
            chunk_size = sum(len(json.dumps(item)) for item in data_chunk if item.get("name") != "other") if data_chunk else 0
            process_speed_mbps = (chunk_size * 8) / (process_elapsed * 1_000_000) if process_elapsed > 0 else 0
            logger.info(f"main: Wrote chunk of {len([item for item in data_chunk if item.get('name') != 'other'])} items, {chunk_size} bytes in {process_elapsed:.3f} s, speed: {process_speed_mbps:.3f} Mbps")
        output_file.write("\n]")
    fetcher.join()
    logger.info(f"main: Data has been written to '{output_filename}'")

if __name__ == "__main__":
    main()