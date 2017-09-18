#!/bin/bash

TMPDIR=`mktemp -d`

# Shift till docker parameters
while [[ -n "$1" && $1 != '--' ]]; do SCENARIOS="$SCENARIOS $1"; echo $SCENARIOS; shift; done
if [[ "$1" = '--' ]]; then shift; fi

if [[ -z "$SCENARIOS" ]]; then
	SCENARIOS=`ls docker/Dockerfile.* | rev | cut -d. -f-1 | rev`
fi

function cleanup() {
	if [[ -d $TMPDIR ]]; then
		rm -fr $TMPDIR
	fi
}

function create_dockerdir() {
	scenario=$1

	cp docker/Dockerfile.$scenario $TMPDIR/Dockerfile
	cp docker/files/* $TMPDIR
}

trap cleanup EXIT

FAILED=""

for SCENARIO in $SCENARIOS; do
	create_dockerdir $SCENARIO
	docker build -t repoman_test_$SCENARIO $TMPDIR && \
	docker run -i -t -v $PWD:/source repoman_test_$SCENARIO "$@" || \
	FAILED="$FAILED $SCENARIO"
done

if [[ -n "$FAILED" ]]; then
	echo "Run failed in: $FAILED"
	exit -1
fi
