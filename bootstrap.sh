#!/bin/bash

virtualenv venv
source ./venv/bin/activate
pip install tox virtualenv

echo "Virtualenv (./venv) is ready to use."
