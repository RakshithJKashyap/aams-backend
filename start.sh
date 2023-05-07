#!/bin/bash

# Start the server
celery -A cworker worker --pool threads --concurrency 4 -ldebug