import asyncio
import logging
import math
import socket
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from pyrtcm import RTCMReader


@dataclass
class BaseStationStatus:
    """Base station status data."""

    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    accuracy_mm: int = 0
    is_fixed_mode: bool = False
    is_survey_in_active: bool = False
    survey_in_duration: int = 0


def ecef_to_geodetic(x: float, y: float, z: float) -> tuple:
    """Convert ECEF coordinates to geodetic coordinates."""
    a = 6378137.0  # semi-major axis in meters
    f = 1 / 298.257223563  # flattening
    e2 = 2 * f - f**2  # square of eccentricity

    b = a * (1 - f)
    ep2 = (a**2 - b**2) / b**2
    p = math.sqrt(x**2 + y**2)
    theta = math.atan2(z * a, p * b)
    lon = math.atan2(y, x)
    lat = math.atan2(
        z + ep2 * b * math.sin(theta) ** 3, p - e2 * a * math.cos(theta) ** 3
    )
    N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    height = p / math.cos(lat) - N

    return math.degrees(lat), math.degrees(lon), height


class GnssMonitor:
    """Monitor GNSS base station status."""

    def __init__(self):
        self._logger = logging.getLogger("base-station-monitor")
        self.status = BaseStationStatus()
        self._socket = None
        self.HOST = "localhost"
        self.PORT = 50010
        self._buffer = bytearray()

    async def connect(self):
        """Establish connection to GNSS socket."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self.HOST, self.PORT))
            self._socket.setblocking(False)
            self._logger.info(f"Connected to GNSS socket at {self.HOST}:{self.PORT}")
        except Exception as e:
            self._logger.error(f"Failed to connect to GNSS socket: {e}")
            self._socket = None

    async def update_status(self) -> Optional[BaseStationStatus]:
        """Read base station status from GNSS socket."""
        if not self._socket:
            await self.connect()
            if not self._socket:
                return None

        try:
            # Read data from socket
            data = await asyncio.get_event_loop().sock_recv(self._socket, 1024)
            if data:
                # Append new data to buffer
                self._buffer.extend(data)

                # Process complete messages
                while len(self._buffer) > 0:
                    # Create RTCMReader for parsing
                    stream = BytesIO(self._buffer)
                    rtr = RTCMReader(stream)

                    try:
                        # Attempt to read a message
                        raw_data, parsed_data = rtr.read()
                        if parsed_data:
                            if parsed_data.identity == "1005":
                                # Process RTCM 1005 message
                                lat, lon, height = ecef_to_geodetic(
                                    parsed_data.DF025,
                                    parsed_data.DF026,
                                    parsed_data.DF027,
                                )
                                self.status.latitude = round(lat, 8)  # cm precision
                                self.status.longitude = round(lon, 8)  # cm precision
                                self.status.altitude = round(height, 2)  # cm precision

                            # Remove processed message from buffer
                            self._buffer = self._buffer[len(raw_data) :]
                        else:
                            # Not enough data for a complete message
                            break
                    except Exception as parse_error:
                        # Remove first byte and try again
                        self._buffer = self._buffer[1:]
                        continue

            return self.status

        except Exception as e:
            self._logger.error(f"Error reading from GNSS socket: {e}")
            self._socket = None
            return None

    async def cleanup(self):
        """Properly close the socket connection."""
        if self._socket:
            self._socket.close()
            self._socket = None

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.cleanup()
