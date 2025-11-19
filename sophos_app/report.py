"""Reporting utilities for Sophos WFH detection.

This module contains helper functions to classify endpoints based on their
reported IP addresses, generate CSV reports and summarise counts.  It
relies on Python's built-in ``ipaddress`` module for subnet comparisons.
"""

from __future__ import annotations

import csv
import ipaddress
import logging
from typing import Dict, Iterable, List, Tuple


LOGGER = logging.getLogger(__name__)


def classify_ip(
    ip_str: str, office_networks: List[ipaddress._BaseNetwork]
) -> str:
    """Determine whether an IP belongs to an office network.

    Returns "Office" if the address is in one of the office networks,
    "Work From Home" otherwise, and "Unknown" on parse failure.
    """
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        LOGGER.debug("Invalid IP address: %s", ip_str)
        return "Unknown"
    for net in office_networks:
        if ip_obj.version != net.version:
            continue
        if ip_obj in net:
            return "Office"
    return "Work From Home"


def classify_endpoint(
    endpoint: Dict[str, object], office_networks: List[ipaddress._BaseNetwork]
) -> Tuple[str, str, str, List[str]]:
    """Classify an endpoint as Office, WFH or Unknown.

    Returns a tuple of (hostname, username, classification, ipv4_list).
    """
    hostname = endpoint.get("hostname") or endpoint.get("name") or "(unknown-host)"
    person = endpoint.get("associatedPerson") or {}
    raw_username = person.get("name") or person.get("username") or "(unknown-user)"
    username = raw_username.split("\\")[-1]
    ipv4s = endpoint.get("ipv4Addresses") or []
    classification = "Unknown"
    if ipv4s:
        classification = "Work From Home"
        for ip in ipv4s:
            if classify_ip(ip, office_networks) == "Office":
                classification = "Office"
                break
    return hostname, username, classification, ipv4s


def generate_report(
    endpoints: Iterable[Dict[str, object]],
    office_subnet_strs: List[str],
    report_path: str,
) -> Tuple[int, int, int]:
    """Create a CSV report summarising endpoint classifications.

    Args:
        endpoints: iterable of endpoint objects returned by the API.
        office_subnet_strs: list of CIDR strings for office networks.
        report_path: filesystem path where the CSV will be written.

    Returns:
        (office_count, wfh_count, unknown_count)
    """
    office_networks: List[ipaddress._BaseNetwork] = []
    for subnet in office_subnet_strs:
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            office_networks.append(network)
        except ValueError:
            LOGGER.warning("Invalid CIDR '%s' ignored", subnet)

    office_count = wfh_count = unknown_count = 0
    with open(report_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Hostname", "Username", "Classification"])
        for ep in endpoints:
            host, user, cls, ips = classify_endpoint(ep, office_networks)
            if cls == "Office":
                office_count += 1
            elif cls == "Work From Home":
                wfh_count += 1
            else:
                unknown_count += 1
            writer.writerow([host, user, cls])
    LOGGER.info(
        "Report written to %s: %d office, %d WFH, %d unknown", report_path, office_count, wfh_count, unknown_count
    )
    return office_count, wfh_count, unknown_count