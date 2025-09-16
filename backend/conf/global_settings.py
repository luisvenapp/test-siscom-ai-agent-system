"""
Default FastAPI settings. Override these with settings in the module pointed to
by the FASTAPI_CONFIG environment variable.
"""

PROJECT_NAME = "FastAPI Project"
PROJECT_DESCRIPTION = ""
PROJECT_VERSION = "0.1.0"

DEBUG = False

CORS_SETTINGS = {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

PAGE_SIZE = 10
