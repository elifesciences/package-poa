#!/bin/bash
set -e
. install.sh
source venv/bin/activate
pip install pip wheel --upgrade
pip install -r requirements.txt
coverage run -m pytest
