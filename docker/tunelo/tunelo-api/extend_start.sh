#!/bin/bash

# Bootstrap and exit if KOLLA_BOOTSTRAP variable is set. This catches all cases
# of the KOLLA_BOOTSTRAP variable being set, including empty.
if [[ "${!KOLLA_BOOTSTRAP[@]}" ]]; then
    exit 0
fi

if [[ "${!KOLLA_UPGRADE[@]}" ]]; then
    exit 0
fi

if [[ "${!KOLLA_OSM[@]}" ]]; then
    exit 0
fi

. /usr/local/bin/kolla_httpd_setup
