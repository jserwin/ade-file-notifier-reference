import azure.functions as func
import logging
import os
import json
from shared.azure_handler import (
    AzureFileHandler,
    download_config
)
from shared.notifier_common import (
    identify_sources,
    construct_folder_path
)

def queue_file(msg: func.QueueMessage):
    """Triggered as messages are added to Azure Queue storage.
    Gets configuration, identifies data source, adds file to queued folder if the source is identified.
        
    Args:
        msg (azure.functions.QueueMessage): Azure Queue storage message which triggers the function.

    Returns:
        None.
    """

    try:
        event_data = msg.get_json()
        container_name = os.getenv('container_name')
        config_prefix = os.getenv('config_prefix')
        config_dict = download_config(container_name, config_prefix)
        blob_url = f"{event_data['data']['blobUrl']}"
        sources = identify_sources(blob_url, config_dict)

        if (sources == [] or not sources):
            logging.info(f'Source not identified for url: {blob_url}')
            return

        for source in sources:
            logging.info(f"Processing source: {source['id']}")
            folder_path = construct_folder_path(source)
            filename = blob_url.split('/')[-1]

            # Construct the full Blob path for the file
            file_path = f"queued/{folder_path}/{filename}.json"
            file_data = json.dumps({"full_file_path": blob_url, "original_event": event_data})

            azure_handler = AzureFileHandler(container_name, "queued/")
            upload_result = azure_handler.upload_file(file_path, file_data)

            if upload_result:
                logging.info(f"Uploaded file to Azure Blob Storage: {file_path}")
            else:
                logging.error(f"Failed to upload {file_path} to Azure Blob Storage.")
                return
        return
    except Exception as e:
        logging.error(f"Error processing event: {event_data}")
        raise