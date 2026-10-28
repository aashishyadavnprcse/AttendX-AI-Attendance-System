"""
AttendX Backend — Geofencing & Network Security Validation Engine
Enforces:
1. Haversine distance geofencing (Distance <= 20.0 meters from classroom anchor).
2. Campus IP Subnet validation (CIDR format e.g. 192.168.1.0/24 or 10.0.0.0/16).
3. Classroom Wi-Fi Access Point Hardware BSSID verification.
"""

import ipaddress
import math
import re
from typing import Optional, Tuple
from fastapi import HTTPException, status

EARTH_RADIUS_METERS = 6371000.0


def calculate_haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Computes great-circle distance between two GPS coordinates using the Haversine formula.
    Returns distance in meters.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = EARTH_RADIUS_METERS * c
    return round(distance, 2)


def is_ip_in_allowed_subnets(client_ip: str, allowed_subnets_str: Optional[str]) -> bool:
    """
    Validates whether the client IP falls within permitted campus CIDR subnets.
    Supports comma-separated subnets e.g. '192.168.1.0/24, 10.10.0.0/16'.
    """
    if not allowed_subnets_str or not allowed_subnets_str.strip():
        return True  # No network restriction configured

    try:
        ip_obj = ipaddress.ip_address(client_ip.strip())
    except ValueError:
        return False

    subnets = [s.strip() for s in allowed_subnets_str.split(",") if s.strip()]
    for subnet in subnets:
        try:
            net_obj = ipaddress.ip_network(subnet, strict=False)
            if ip_obj in net_obj:
                return True
        except ValueError:
            continue

    return False


def normalize_mac_address(mac: Optional[str]) -> Optional[str]:
    """Standardizes MAC address / BSSID to lowercase colon-separated format."""
    if not mac:
        return None
    cleaned = re.sub(r"[^0-9a-fA-F]", "", mac.lower())
    if len(cleaned) == 12:
        return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))
    return mac.strip().lower()


def is_valid_wifi_bssid(reported_bssid: Optional[str], allowed_bssid: Optional[str]) -> bool:
    """Validates device Wi-Fi Access Point BSSID against registered classroom router."""
    if not allowed_bssid or not allowed_bssid.strip():
        return True  # No BSSID restriction configured

    norm_reported = normalize_mac_address(reported_bssid)
    norm_allowed = normalize_mac_address(allowed_bssid)

    return norm_reported is not None and norm_reported == norm_allowed


def validate_geofence_and_network_security(
    device_latitude: Optional[float],
    device_longitude: Optional[float],
    classroom_latitude: float,
    classroom_longitude: float,
    max_radius_meters: float = 20.0,
    client_ip: Optional[str] = None,
    allowed_subnets: Optional[str] = None,
    device_bssid: Optional[str] = None,
    allowed_bssid: Optional[str] = None,
    enforce_geofence: bool = True,
    enforce_network: bool = False,
) -> Tuple[bool, float, str]:
    """
    Comprehensive security gatekeeper validating physical proximity and network boundaries.
    Throws HTTPException(403) with structured audit details upon breach.
    """
    # 1. Geofence Distance Validation
    if enforce_geofence:
        if device_latitude is None or device_longitude is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "GPS_COORDINATES_MISSING",
                    "message": "Physical presence verification requires valid GPS coordinates.",
                },
            )

        distance = calculate_haversine_distance(
            device_latitude,
            device_longitude,
            classroom_latitude,
            classroom_longitude,
        )

        if distance > max_radius_meters:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "GEOLOCATION_BREACH",
                    "message": f"Attendance rejected. Distance from classroom is {distance:.1f}m (exceeds allowable {max_radius_meters:.1f}m threshold).",
                    "calculated_distance_meters": distance,
                    "max_allowed_meters": max_radius_meters,
                    "device_coords": {"lat": device_latitude, "lon": device_longitude},
                    "classroom_coords": {"lat": classroom_latitude, "lon": classroom_longitude},
                },
            )
    else:
        distance = 0.0

    # 2. Campus IP Subnet Validation
    if enforce_network and allowed_subnets:
        if not client_ip or not is_ip_in_allowed_subnets(client_ip, allowed_subnets):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "NETWORK_SUBNET_BREACH",
                    "message": f"Device IP '{client_ip}' is outside authorized campus subnets: {allowed_subnets}.",
                },
            )

    # 3. Wi-Fi Access Point BSSID Validation
    if allowed_bssid:
        if not is_valid_wifi_bssid(device_bssid, allowed_bssid):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "WIFI_BSSID_BREACH",
                    "message": "Device is not connected to the authorized classroom Wi-Fi access point.",
                    "reported_bssid": device_bssid,
                    "required_bssid": allowed_bssid,
                },
            )

    return True, distance, f"Physical & network security validated. Distance: {distance:.1f}m."
