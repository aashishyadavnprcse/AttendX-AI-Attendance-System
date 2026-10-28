/// AttendX — Flutter Cross-Platform Geofencing & Wi-Fi BSSID Security Service
/// Requires: geolocator: ^11.0.0, network_info_plus: ^5.0.1
import 'dart:math';

class Coordinates {
  final double latitude;
  final double longitude;
  final double accuracy;

  Coordinates({
    required this.latitude,
    required this.longitude,
    this.accuracy = 0.0,
  });
}

class GeofenceVerification {
  final double distanceMeters;
  final bool isInside;
  final String status;

  GeofenceVerification({
    required this.distanceMeters,
    required this.isInside,
    required this.status,
  });
}

class AttendXGeoSecurityService {
  static const double earthRadiusMeters = 6371000.0;
  static const double maxAllowedRadiusMeters = 20.0;

  /// Calculates Haversine distance in meters between two lat/lon coordinates
  static double calculateHaversineDistance(
    Coordinates device,
    Coordinates classroom,
  ) {
    double toRad(double degree) => degree * pi / 180.0;

    final dLat = toRad(classroom.latitude - device.latitude);
    final dLon = toRad(classroom.longitude - device.longitude);

    final lat1 = toRad(device.latitude);
    final lat2 = toRad(classroom.latitude);

    final a = sin(dLat / 2) * sin(dLat / 2) +
        sin(dLon / 2) * sin(dLon / 2) * cos(lat1) * cos(lat2);
    final c = 2 * atan2(sqrt(a), sqrt(1 - a));

    return earthRadiusMeters * c;
  }

  /// Verifies if student device is within allowed classroom perimeter
  static GeofenceVerification verifyProximity({
    required Coordinates device,
    required Coordinates classroom,
    double radiusMeters = maxAllowedRadiusMeters,
  }) {
    final distance = calculateHaversineDistance(device, classroom);
    final isInside = distance <= radiusMeters;

    return GeofenceVerification(
      distanceMeters: double.parse(distance.toStringAsFixed(2)),
      isInside: isInside,
      status: isInside ? "INSIDE_GEOFENCE" : "OUTSIDE_GEOFENCE",
    );
  }
}
