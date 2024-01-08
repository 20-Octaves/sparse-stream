#!/bin/bash

set -euo pipefail
trap 'rc=$?;set +ex;if [[ $rc -ne 0 ]];then trap - ERR EXIT;echo 1>&2;echo "*** fail *** : code $rc : $DIR/$SCRIPT $ARGS" 1>&2;echo 1>&2;exit $rc;fi' ERR
ARGS="$*"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$(basename "${BASH_SOURCE[0]}")"


tag=octv

repo=localhost/$tag

cd $DIR

containerizer=podman
#containerizer=docker

set -x

$containerizer buildx build -f octv.df -t $repo .
#$containerizer  build -f octv.df -t $repo .

$containerizer run --rm --name $tag $repo
