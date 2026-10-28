import { useState, useEffect, useCallback } from 'react';
import {
  Coordinates,
  GeofenceResult,
  calculateHaversineDistance,
  getCurrentDeviceLocation,
  evaluateGeofence,
} from '../utils/geoFence';

export interface UseGeoFencingOptions {
  classroomCoords: Coordinates;
  maxRadiusMeters?: number; // Defaults to 20.0 meters per AttendX policy
  autoWatch?: boolean;
}

export interface UseGeoFencingReturn {
  deviceLocation: Coordinates | null;
  distanceMeters: number | null;
  isInside: boolean;
  accuracyMeters: number | null;
  status: 'IDLE' | 'LOCATING' | 'INSIDE' | 'OUTSIDE' | 'ERROR';
  errorMessage: string | null;
  refreshLocation: () => Promise<GeofenceResult | null>;
}

/**
 * Custom React Hook for live AttendX Geofencing verification.
 * Automatically checks distance against classroom anchor point.
 */
export function useGeoFencing({
  classroomCoords,
  maxRadiusMeters = 20.0,
  autoWatch = true,
}: UseGeoFencingOptions): UseGeoFencingReturn {
  const [deviceLocation, setDeviceLocation] = useState<Coordinates | null>(null);
  const [distanceMeters, setDistanceMeters] = useState<number | null>(null);
  const [isInside, setIsInside] = useState<boolean>(false);
  const [accuracyMeters, setAccuracyMeters] = useState<number | null>(null);
  const [status, setStatus] = useState<UseGeoFencingReturn['status']>('IDLE');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const checkLocation = useCallback(async (): Promise<GeofenceResult | null> => {
    setStatus('LOCATING');
    setErrorMessage(null);

    try {
      const coords = await getCurrentDeviceLocation();
      setDeviceLocation(coords);
      setAccuracyMeters(coords.accuracy ?? null);

      const result = evaluateGeofence(coords, classroomCoords, maxRadiusMeters);
      setDistanceMeters(result.distanceMeters);
      setIsInside(result.isInside);

      if (result.status === 'INSIDE_GEOFENCE') {
        setStatus('INSIDE');
      } else {
        setStatus('OUTSIDE');
        if (result.status === 'INACCURATE_GPS') {
          setErrorMessage(
            `GPS accuracy (${result.accuracyMeters.toFixed(1)}m) is too degraded. Please step near a window.`
          );
        }
      }

      return result;
    } catch (err: any) {
      setStatus('ERROR');
      setErrorMessage(err.message || 'Unable to retrieve location.');
      setIsInside(false);
      return null;
    }
  }, [classroomCoords, maxRadiusMeters]);

  useEffect(() => {
    if (!autoWatch) return;

    // Initial check
    checkLocation();

    // Continuous position watcher for high-security classrooms
    let watchId: number | null = null;
    if (navigator.geolocation) {
      watchId = navigator.geolocation.watchPosition(
        (pos) => {
          const coords: Coordinates = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
          };
          setDeviceLocation(coords);
          setAccuracyMeters(coords.accuracy);

          const distance = calculateHaversineDistance(coords, classroomCoords);
          setDistanceMeters(distance);
          const inside = distance <= maxRadiusMeters;
          setIsInside(inside);
          setStatus(inside ? 'INSIDE' : 'OUTSIDE');
        },
        (err) => {
          setErrorMessage(err.message);
          setStatus('ERROR');
        },
        { enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }
      );
    }

    return () => {
      if (watchId !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchId);
      }
    };
  }, [autoWatch, checkLocation, classroomCoords, maxRadiusMeters]);

  return {
    deviceLocation,
    distanceMeters,
    isInside,
    accuracyMeters,
    status,
    errorMessage,
    refreshLocation: checkLocation,
  };
}
