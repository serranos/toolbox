import logging
import sys

# Possible values: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOGGING_LEVEL = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

# Database configuration parameters
DB_NAME = 'database.db'

# The time period between URL updates
CRAWLER_UPDATE_DELTA = 86400

# The Crawler refresh period. Used if no URLs left to crawl at that instant.
CRAWLER_REFRESH_PERIOD = 300

# The Crawler User-Agent
CRAWLER_USER_AGENT = {'User-agent': 'Mozilla/5.0 YetAnotherWebCrawler 0.1'}

# Available Get operations to the user
OPERATION_GET = 1
OPERATION_ALL = 2

# Status of the URL
URL_STATUS_PROCESSING = 0
URL_STATUS_TODO = 1
URL_STATUS_DONE = 2
ALLOWED_URL_SCHEMES = ['http', 'https']
