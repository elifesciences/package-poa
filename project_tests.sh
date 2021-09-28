#!/bin/bash
set -e
. mkvenv.sh
source venv/bin/activate
pip install coveralls wheel pip pytest --upgrade
pip install -r requirements.txt
coverage run -m pytest
