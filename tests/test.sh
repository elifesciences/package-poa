#!/bin/bash
set -e

# test printing to stdout
echo "test message"

# test printing to sterr
>&2 echo "test error message"
