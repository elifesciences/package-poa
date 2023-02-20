#!/bin/bash
set -e

# test printing to stdout
echo "test message"

# test printing to stderr
>&2 echo "test error message"
