"""Detect public IPv4 addresses for direct HTTP and HTTPS routes."""

import http.client
import ipaddress
import json
import urllib.request


def detect_addresses():
    direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with direct.open("https://api.ipify.org", timeout=15) as response:
        https_address = str(ipaddress.IPv4Address(response.read().decode().strip()))

    connection = http.client.HTTPConnection("checkip.amazonaws.com", 80, timeout=15)
    try:
        connection.request("GET", "/")
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError("HTTP egress address check failed.")
        http_address = str(ipaddress.IPv4Address(response.read().decode().strip()))
    finally:
        connection.close()
    return sorted({http_address, https_address})


if __name__ == "__main__":
    print(json.dumps(detect_addresses()))
