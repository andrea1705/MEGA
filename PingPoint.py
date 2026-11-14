"""
pingpoint.py

Command-line tool that reports the host's public IPv4 and IPv6 addresses
along with ISP, ASN and geolocation details.

How it works:
    1. ipify (api.ipify.org / api6.ipify.org) returns the public IP. The
       IPv4 and IPv6 endpoints are separate, so each is queried on its own.
    2. ipapi.co returns ISP, ASN and location data for one of those IPs.
    3. The results are printed as a report. The user can refresh or quit.

Requirements:
    Python 3.8+ and the "requests" package (pip install requests).
    No API keys are needed, but ipapi.co limits free usage, so repeated
    refreshes may eventually return a rate-limit error.

Usage:
    python pingpoint.py

"""

import sys
from datetime import datetime

import requests

# ipify returns {"ip": "<address>"}. The api6 host only answers over IPv6,
# which is how we tell whether the network has IPv6 connectivity.
IPV4_ENDPOINT = "https://api.ipify.org?format=json"
IPV6_ENDPOINT = "https://api6.ipify.org?format=json"

# ipapi.co lookup URL is built as {base}/{ip}/json/
GEO_BASE_URL = "https://ipapi.co"

# Seconds to wait before giving up on a request, so a dead route
# doesn't leave the tool hanging.
REQUEST_TIMEOUT = 5


def get_public_ip(endpoint, ip_version):
    """
    Query an ipify endpoint and return the public IP as a string.

    endpoint:   URL to query (IPV4_ENDPOINT or IPV6_ENDPOINT).
    ip_version: "IPv4" or "IPv6", used only in the error messages.

    This function never raises. On failure it returns a human-readable
    message instead of an IP, and the rest of the program treats any
    string containing a space as "not a valid IP". If you change these
    messages, keep that in mind (see main() and get_ip_metadata()).
    """
    try:
        response = requests.get(endpoint, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json().get("ip", "Unavailable")
    except requests.exceptions.ConnectionError:
        # Usually means the network has no route for this IP version,
        # most often because the ISP or router doesn't support IPv6.
        return f"Not Detected (No {ip_version} route)"
    except requests.exceptions.Timeout:
        return f"Timeout ({ip_version} request exceeded {REQUEST_TIMEOUT}s)"
    except requests.exceptions.RequestException as err:
        # Catch-all for anything else (bad status code, invalid JSON, etc.)
        return f"Error ({err})"


def get_ip_metadata(ip_address):
    """
    Look up ISP, ASN and geolocation data for an IP using ipapi.co.

    Returns the parsed JSON dict on success. On any failure it returns
    {"error": "<message>"}, so callers only need to check for the
    "error" key.
    """
    # A space means get_public_ip() returned an error message, not an IP.
    if not ip_address or " " in ip_address:
        return {"error": "Valid IP required for metadata lookup."}

    url = f"{GEO_BASE_URL}/{ip_address}/json/"
    # ipapi.co may reject requests that have no User-Agent.
    headers = {"User-Agent": "DEVASC-NetTech-IP-Tool/1.0"}

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as err:
        return {"error": f"Metadata fetch failed: {err}"}

    # ipapi.co can return HTTP 200 with {"error": true, "reason": "..."}
    # (for example when the rate limit is hit), so check the body as well.
    if data.get("error"):
        return {"error": data.get("reason", "API returned an error.")}
    return data


def display_report(ipv4, ipv6, meta):
    """
    Print the diagnostic report to the terminal.

    ipv4, ipv6: strings from get_public_ip() (an IP or an error message).
    meta:       dict from get_ip_metadata().

    To add a new field to the report, read it from `meta` in the else
    branch below and print it with the same format. Available keys are
    listed at https://ipapi.co/api/#complete-location5
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    border = "=" * 62

    print(f"\n{border}")
    print("  NETWORK TECHNICIAN IP DIAGNOSTIC REPORT")
    print(f"  Generated: {timestamp}")
    print(border)
    print(f"  {'Public IPv4 Address':<24}: {ipv4}")
    print(f"  {'Public IPv6 Address':<24}: {ipv6}")
    print("-" * 62)

    if "error" in meta:
        print(f"  {'Network Metadata':<24}: {meta['error']}")
    else:
        # .get() with "N/A" so a missing field doesn't crash the report
        country = f"{meta.get('country_name', 'N/A')} ({meta.get('country_code', 'N/A')})"
        coords = f"{meta.get('latitude', 'N/A')}, {meta.get('longitude', 'N/A')}"
        location = f"{meta.get('city', 'N/A')}, {meta.get('region', 'N/A')}"

        print(f"  {'ISP / Organization':<24}: {meta.get('org', 'N/A')}")
        print(f"  {'ASN':<24}: {meta.get('asn', 'N/A')}")
        print(f"  {'City / Region':<24}: {location}")
        print(f"  {'Country':<24}: {country}")
        print(f"  {'Coordinates (Lat, Lon)':<24}: {coords}")
        print(f"  {'Timezone':<24}: {meta.get('timezone', 'N/A')}")

    print(f"{border}\n")


def main():
    """
    Run the tool: fetch IPs, look up metadata, print the report, then
    ask whether to refresh or quit. Loops until the user quits.
    """
    print("Initializing IPv4/IPv6 Diagnostic Tool...")

    while True:
        ipv4 = get_public_ip(IPV4_ENDPOINT, "IPv4")
        ipv6 = get_public_ip(IPV6_ENDPOINT, "IPv6")

        # Metadata is looked up for one IP only. IPv4 is preferred; IPv6 is
        # the fallback when IPv4 failed (a failed result contains a space).
        target_ip = ipv4 if " " not in ipv4 else ipv6
        display_report(ipv4, ipv6, get_ip_metadata(target_ip))

        choice = input("Press [R] to refresh diagnostics or [Q] to quit: ").strip().lower()
        if choice != "r":
            print("Exiting IP Diagnostic Tool.")
            sys.exit(0)


if __name__ == "__main__":
    main()