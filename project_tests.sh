#!/bin/bash

tox
. .tox/py3/bin/activate
pip install coveralls
COVERALLS_REPO_TOKEN=$(cat /etc/coveralls/tokens/package-poa) coveralls
