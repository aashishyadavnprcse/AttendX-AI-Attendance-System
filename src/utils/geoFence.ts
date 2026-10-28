/**
 * AttendX — Geofencing & Network Security Utilities
 * High-precision GPS Haversine calculation, browser Geolocation API wrapper,
 * and device network metadata extraction.
 */

export interface Coordinates {
  latitude: number;
  longitude: number;
  accuracy?: number;
}

export interface GeofenceResult {
  distanceMeters: number;
  isInside: boolean;
  maxRadiusMeters: number;
  accuracyMeters: number;
  status: 'INSIDE_GEOFENCE' | 'OUTSIDE_GEOFENCE' | 'INACCURATE_GPS';
}

export interface NetworkInfo {
  ipAddress?: string;
  wifiBssid?: string;
  effectiveType?: string;
  downlinkSpeedMbps?: number;
  roundTripTimeMs?: number;
}

// Earth's mean radius in meters
const EARTH_RADIUS_METERS = 6371000;

/**
 * Calculates high-precision distance between two geographic coordinates using the Haversine formula.
 * @param coord1 Device GPS coordinates
 * @param coord2 Classroom anchor coordinates
 * @returns Distance in meters (rounded to 2 decimal places)
 */
export function calculateHaversineDistance(
  coord1: Coordinates,
  coord2: Coordinates
): number {
  const toRadians = (degrees: number) => (degrees * Math.PI) / 180;

  const lat1Rad = toRadians(coord1.latitude);
  const lat2Rad = toRadians(coord2.latitude);
  const deltaLatRad = toRadians(coord2.latitude - coord1.latitude);
  const deltaLonRad = toRadians(coord2.longitude - coord1.longitude);

  const a =
    Math.sin(deltaLatRad / 2) * Math.sin(deltaLatRad / 2) +
    Math.cos(lat1Rad) *
      Math.cos(lat2Rad) *
      Math.sin(deltaLonRad / 2) *
      Math.sin(deltaLonRad / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const distance = EARTH_RADIUS_METERS * c;

  return Math.round(distance * 100) / 100;
}

/**
 * Fetches high-accuracy GPS coordinates using the browser's Geolocation API.
 * Automatically configures maximum accuracy flags to prevent cell-tower approximation.
 */
export function getCurrentDeviceLocation(
  timeoutMs: number = 10000
): Promise<Coordinates> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation is not supported by your browser or device.'));
      return;
    }

    const options: PositionOptions = {
      enableHighAccuracy: true, // Forces GPS sensor instead of IP lookup
      timeout: timeoutMs,
      maximumAge: 0, // Invalidate cached positions
    };

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
      },
      (error) => {
        let msg = 'Failed to obtain GPS coordinates.';
        switch (error.code) {
          case error.PERMISSION_DENIED:
            msg = 'Location permission denied. Please enable GPS permissions to mark attendance.';
            break;
          case error.POSITION_UNAVAILABLE:
            msg = 'GPS signal unavailable. Ensure location services are turned on.';
            break;
          case error.TIMEOUT:
            msg = 'GPS request timed out. Please try again in an area with clear sky visibility.';
            break;
        }
        reject(new Error(msg));
      },
      options
    );
  });
}

/**
 * Validates whether device coordinates fall within the allowed classroom perimeter.
 */
export function evaluateGeofence(
  deviceCoords: Coordinates,
  classroomCoords: Coordinates,
  maxRadiusMeters: number = 20.0
): GeofenceResult {
  const distance = calculateHaversineDistance(deviceCoords, classroomCoords);
  const accuracy = deviceCoords.accuracy ?? 5.0;

  // If GPS inaccuracy is worse than 35 meters, alert for potential spoofing/poor signal
  if (accuracy > 35.0) {
    return {
      distanceMeters: distance,
      isInside: distance <= maxRadiusMeters,
      maxRadiusMeters,
      accuracyMeters: accuracy,
      status: 'INACCURATE_GPS',
    };
  }

  const isInside = distance <= maxRadiusMeters;

  return {
    distanceMeters: distance,
    isInside,
    maxRadiusMeters,
    accuracyMeters: accuracy,
    status: isInside ? 'INSIDE_GEOFENCE' : 'OUTSIDE_GEOFENCE',
  };
}

/**
 * Captures network connection telemetry using Network Information API when supported.
 */
export function getClientNetworkTelemetry(): NetworkInfo {
  const nav = navigator as any;
  const connection =
    nav.connection || nav.mozConnection || nav.webkitConnection;

  if (connection) {
    return {
      effectiveType: connection.effectiveType, // '4g', 'wifi', etc.
      downlinkSpeedMbps: connection.downlink,
      roundTripTimeMs: connection.rtt,
    };
  }

  return {};
}
