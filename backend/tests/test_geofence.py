"""
AttendX Unit Test Suite — Geofencing & Network Security Validation
Tests Haversine calculation, 20m perimeter enforcement, IP subnet CIDR, and Wi-Fi BSSID checking.
"""

import sys
from pathlib import Path
from fastapi import HTTPException

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.services.geofence_validator import (
    calculate_haversine_distance,
    is_ip_in_allowed_subnets,
    is_valid_wifi_bssid,
    validate_geofence_and_network_security,
)


def run_geofence_tests():
    print("==================================================================")
    print(" AttendX Geofencing & Network Security Validation Tests")
    print("==================================================================")

    # Classroom coordinates (Anchor)
    classroom_lat = 37.774929
    classroom_lon = -122.419416

    # Test 1: Device within 8 meters (Inside classroom)
    device_inside_lat = 37.774970
    device_inside_lon = -122.419450
    dist_inside = calculate_haversine_distance(
        device_inside_lat, device_inside_lon, classroom_lat, classroom_lon
    )
    print(f"\n[Test 1] Device Inside Classroom: Calculated distance = {dist_inside:.2f}m")
    assert dist_inside <= 20.0, f"Expected <= 20m, got {dist_inside}m"

    valid, dist, msg = validate_geofence_and_network_security(
        device_latitude=device_inside_lat,
        device_longitude=device_inside_lon,
        classroom_latitude=classroom_lat,
        classroom_longitude=classroom_lon,
        max_radius_meters=20.0,
    )
    assert valid is True
    print(f" -> Result: PASS ({msg})")

    # Test 2: Device at 65 meters (Outside classroom hallway / parking lot)
    device_outside_lat = 37.775450
    device_outside_lon = -122.419900
    dist_outside = calculate_haversine_distance(
        device_outside_lat, device_outside_lon, classroom_lat, classroom_lon
    )
    print(f"\n[Test 2] Device Outside Perimeter: Calculated distance = {dist_outside:.2f}m")
    assert dist_outside > 20.0

    try:
        validate_geofence_and_network_security(
            device_latitude=device_outside_lat,
            device_longitude=device_outside_lon,
            classroom_latitude=classroom_lat,
            classroom_longitude=classroom_lon,
            max_radius_meters=20.0,
        )
        assert False, "Should have thrown HTTPException(403)"
    except HTTPException as exc:
        print(f" -> Result: BLOCKED with HTTP {exc.status_code}")
        print(f" -> Error Detail: {exc.detail['error_code']} - {exc.detail['message']}")
        assert exc.detail["error_code"] == "GEOLOCATION_BREACH"

    # Test 3: Campus IP Subnet CIDR Checking
    print("\n[Test 3] Campus IP Subnet Validation:")
    campus_subnets = "192.168.1.0/24, 10.0.0.0/16"
    assert is_ip_in_allowed_subnets("192.168.1.45", campus_subnets) is True
    print(" -> 192.168.1.45 in 192.168.1.0/24: PASS")
    assert is_ip_in_allowed_subnets("10.0.5.12", campus_subnets) is True
    print(" -> 10.0.5.12 in 10.0.0.0/16: PASS")
    assert is_ip_in_allowed_subnets("203.0.113.195", campus_subnets) is False
    print(" -> 203.0.113.195 outside campus: REJECTED (PASS)")

    # Test 4: Classroom Wi-Fi BSSID Check
    print("\n[Test 4] Classroom Wi-Fi BSSID MAC Checking:")
    classroom_bssid = "00:14:22:01:23:45"
    assert is_valid_wifi_bssid("00:14:22:01:23:45", classroom_bssid) is True
    assert is_valid_wifi_bssid("00-14-22-01-23-45", classroom_bssid) is True
    assert is_valid_wifi_bssid("a4:b2:39:11:82:90", classroom_bssid) is False
    print(" -> BSSID normalizer & comparator: PASS")

    print("\n==================================================================")
    print(" ALL GEOFENCING & NETWORK VALIDATION TESTS PASSED SUCCESSFULLY! ")
    print("==================================================================")


if __name__ == "__main__":
    run_geofence_tests()
