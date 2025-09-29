import os

wx_credentials = {
    "url": os.getenv("IBM_CLOUD_URL"),
    "apikey": os.getenv("WATSONX_APIKEY"),
    "project_id": os.getenv("WATSONX_PROJECT_ID"),
}
