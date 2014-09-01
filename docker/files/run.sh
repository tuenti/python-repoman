#!/bin/bash

if [[ ! -f /source/requirements.txt ]]; then
	echo "Docker needs to see current directory, run docker docker with -v .:/source"
	exit -1
fi

cd /source
pip install -r requirements.txt --src /tmp/pip-src

py.test "$@"
