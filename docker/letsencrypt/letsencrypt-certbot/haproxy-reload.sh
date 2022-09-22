#!/bin/sh 

# Update HAProxy with new certs via its API

le_base=/etc/letsencrypt/live
if [[ -d "$le_base" ]]; then
    domains=$(find $le_base -mindepth 1 -type d -exec basename {} \;)
    for domain in $domains; do
        cert_path="/etc/haproxy/certs.d/$domain.pem"
        # Start a transaction to update the certificate
        echo -e "set ssl cert $cert_path <<\n$(cat $le_base/$domain/fullchain.pem $le_base/$domain/privkey.pem | sed '/^[[:blank:]]*$/ d')\n" | socat /var/lib/kolla/haproxy/haproxy.sock -
        # Commit the transaction
        echo -e "commit ssl cert $cert_path" | socat /var/lib/kolla/haproxy/haproxy.sock -
    done
fi

