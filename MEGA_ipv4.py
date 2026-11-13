"""
Project Activity 3: Option 2 - IPv4/IPv6 Network Technician CLI Tool
Description: Retrieves the host's current public IPv4 and IPv6 addresses,
along with ISP, ASN, and geolocation metadata using public REST APIs.
"""

import requests
import sys
from datetime import datetime

# API Endpoints (No API keys required for standard rate limits)
IPV4_ENDPOINT = "https://api.ipify.org?format=json"
IPV6_ENDPOINT = "https://api6.ipify.org?format=json"
GEO_BASE_URL = "https://ipapi.co"

# Timeout in seconds for HTTP requests to prevent hanging on dead routes
REQUEST_TIMEOUT = 5


def get_public_ip(endpoint: str, ip_version: str) -> str:
    """
    Fetches the public IP address from the given ipify endpoint.
    
    Args:
        endpoint (str): The REST API URL to query.
        ip_version (str): Label for error reporting ('IPv4' or 'IPv6').
        
    Returns:
        str: The detected IP address, or an error/unavailable message.
    """
    try:
        response = requests.get(endpoint, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("ip", "Unavailable")
    except requests.exceptions.ConnectionError:
        # Common if the technician's local ISP/router does not support IPv6
        return f"Not Detected (No {ip_version} route)"
    except requests.exceptions.Timeout:
        return f"Timeout ({ip_version} request exceeded {REQUEST_TIMEOUT}s)"
    except requests.exceptions.RequestException as err:
        return f"Error ({err})"


def get_ip_metadata(ip_address: str) -> dict:
    """
    Retrieves ISP, ASN, and geolocation details for a valid IP address.
    
    Args:
        ip_address (str): A valid public IPv4 or IPv6 address.
        
    Returns:
        dict: Parsed JSON metadata or an error dictionary.
    """
    # Skip lookup if the IP string contains an error/status message
    if not ip_address or " " in ip_address:
        return {"error": "Valid IP required for metadata lookup."}

    url = f"{GEO_BASE_URL}/{ip_address}/json/"
    headers = {"User-Agent": "DEVASC-NetTech-IP-Tool/1.0"}

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            return {"error": data.get("reason", "API returned an error.")}
        return data
    except requests.exceptions.RequestException as err:
        return {"error": f"Metadata fetch failed: {err}"}


def display_report(ipv4: str, ipv6: str, meta: dict) -> None:
    """
    Formats and prints the retrieved network data into a clean terminal table.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    border = "=" * 62

    print(f"\n{border}")
    print(f"  NETWORK TECHNICIAN IP DIAGNOSTIC REPORT")
    print(f"  Generated: {timestamp}")
    print(border)
    print(f"  {'Public IPv4 Address':<24}: {ipv4}")
    print(f"  {'Public IPv6 Address':<24}: {ipv6}")
    print("-" * 62)

    if "error" in meta:
        print(f"  {'Network Metadata':<24}: {meta['error']}")
    else:
        city = meta.get("city", "N/A")
        region = meta.get("region", "N/A")
        country = f"{meta.get('country_name', 'N/A')} ({meta.get('country_code', 'N/A')})"
        isp = meta.get("org", "N/A")
        asn = meta.get("asn", "N/A")
        timezone = meta.get("timezone", "N/A")
        coords = f"{meta.get('latitude', 'N/A')}, {meta.get('longitude', 'N/A')}"

        print(f"  {'ISP / Organization':<24}: {isp}")
        print(f"  {'ASN':<24}: {asn}")
        print(f"  {'City / Region':<24}: {city}, {region}")
        print(f"  {'Country':<24}: {country}")
        print(f"  {'Coordinates (Lat, Lon)':<24}: {coords}")
        print(f"  {'Timezone':<24}: {timezone}")

    print(f"{border}\n")


def main():
    """
    Main execution loop allowing single-run diagnostics or continuous refresh.
    """
    print("Initializing IPv4/IPv6 Diagnostic Tool...")

    while True:
        ipv4 = get_public_ip(IPV4_ENDPOINT, "IPv4")
        ipv6 = get_public_ip(IPV6_ENDPOINT, "IPv6")

        # Prefer IPv4 for geolocation/ISP metadata; fallback to IPv6 if IPv4 fails
        target_ip = ipv4 if " " not in ipv4 else ipv6
        metadata = get_ip_metadata(target_ip)

        display_report(ipv4, ipv6, metadata)

        choice = input("Press [R] to refresh diagnostics or [Q] to quit: ").strip().lower()
        if choice != "r":
            print("Exiting IP Diagnostic Tool.")
            sys.exit(0)


if __name__ == "__main__":
    main()