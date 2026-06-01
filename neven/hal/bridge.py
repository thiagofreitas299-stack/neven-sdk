"""
NEVEN Hardware Abstraction Layer (HAL)

Translates standardized NEVEN commands into protocol-specific payloads
for physical hardware devices.

Supported protocols:
    - RTSP / ONVIF (cameras)
    - MQTT (IoT sensors and actuators)
    - HTTP/REST (smart devices)
    - Modbus (industrial equipment)
    - WEBCAM (local camera devices)
"""

import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from neven.core.models import Device, DeviceProtocol, DeviceStatus

logger = logging.getLogger("neven.hal")


class DriverStatus(str, Enum):
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class CommandResult:
    """Result of a hardware command execution."""
    success: bool
    response_code: str
    message: str
    data: Optional[Dict[str, Any]] = None
    execution_time_ms: float = 0.0


class DeviceDriver:
    """
    Base device driver for hardware communication.

    Each protocol has a specific driver implementation that handles
    the translation from NEVEN commands to hardware signals.
    """

    def __init__(self, device: Device):
        self.device = device
        self.status = DriverStatus.READY
        self._connected = False
        self._last_command_time = 0.0

    def connect(self) -> bool:
        """Establish connection to the physical device."""
        try:
            logger.info(
                f"Connecting to device {self.device.device_id} "
                f"via {self.device.protocol.value} at {self.device.connection_uri}"
            )
            # Protocol-specific connection logic
            self._connected = True
            self.device.status = DeviceStatus.ONLINE
            self.status = DriverStatus.READY
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.status = DriverStatus.ERROR
            return False

    def disconnect(self) -> None:
        """Disconnect from the device."""
        self._connected = False
        self.device.status = DeviceStatus.OFFLINE
        self.status = DriverStatus.DISCONNECTED

    def execute(self, command: str, parameters: Dict[str, Any]) -> CommandResult:
        """
        Execute a command on the physical device.

        Args:
            command: The command to execute (e.g., "unlock", "read_sensor")
            parameters: Command parameters

        Returns:
            CommandResult with success status and response data
        """
        start_time = time.time()

        if not self._connected:
            return CommandResult(
                success=False,
                response_code="0x01_NOT_CONNECTED",
                message="Device not connected",
            )

        self.status = DriverStatus.BUSY

        try:
            # Dispatch to protocol-specific handler
            result = self._dispatch_command(command, parameters)
            self._last_command_time = time.time()
            self.status = DriverStatus.READY

            result.execution_time_ms = (time.time() - start_time) * 1000
            return result

        except Exception as e:
            self.status = DriverStatus.ERROR
            return CommandResult(
                success=False,
                response_code="0xFF_ERROR",
                message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _dispatch_command(self, command: str, parameters: Dict[str, Any]) -> CommandResult:
        """Dispatch command based on device protocol."""
        protocol = self.device.protocol

        if protocol == DeviceProtocol.RTSP or protocol == DeviceProtocol.ONVIF:
            return self._handle_camera_command(command, parameters)
        elif protocol == DeviceProtocol.MQTT:
            return self._handle_mqtt_command(command, parameters)
        elif protocol == DeviceProtocol.HTTP:
            return self._handle_http_command(command, parameters)
        elif protocol == DeviceProtocol.MODBUS:
            return self._handle_modbus_command(command, parameters)
        elif protocol == DeviceProtocol.WEBCAM:
            return self._handle_webcam_command(command, parameters)
        else:
            return CommandResult(
                success=False,
                response_code="0x02_UNSUPPORTED",
                message=f"Unsupported protocol: {protocol}",
            )

    def _handle_camera_command(self, command: str, params: Dict) -> CommandResult:
        """Handle RTSP/ONVIF camera commands."""
        if command == "start_stream":
            return CommandResult(
                success=True,
                response_code="0x00_SUCCESS",
                message="Stream started",
                data={"stream_url": self.device.connection_uri},
            )
        elif command == "ptz_move":
            return CommandResult(
                success=True,
                response_code="0x00_SUCCESS",
                message=f"PTZ moved: pan={params.get('pan')}, tilt={params.get('tilt')}",
            )
        elif command == "snapshot":
            return CommandResult(
                success=True,
                response_code="0x00_SUCCESS",
                message="Snapshot captured",
                data={"format": "jpeg"},
            )
        return CommandResult(
            success=False,
            response_code="0x03_UNKNOWN_CMD",
            message=f"Unknown camera command: {command}",
        )

    def _handle_mqtt_command(self, command: str, params: Dict) -> CommandResult:
        """Handle MQTT IoT commands."""
        if command == "publish":
            topic = params.get("topic", "neven/default")
            payload = params.get("payload", {})
            return CommandResult(
                success=True,
                response_code="0x00_SUCCESS",
                message=f"Published to {topic}",
                data={"topic": topic, "payload": payload},
            )
        elif command == "read_sensor":
            return CommandResult(
                success=True,
                response_code="0x00_SUCCESS",
                message="Sensor read",
                data={"value": params.get("default_value", 0)},
            )
        elif command == "unlock_compartment":
            compartment = params.get("compartment_id", "unknown")
            return CommandResult(
                success=True,
                response_code="0x00_SUCCESS",
                message=f"Compartment {compartment} unlocked",
                data={"compartment_id": compartment, "state": "unlocked"},
            )
        return CommandResult(
            success=False,
            response_code="0x03_UNKNOWN_CMD",
            message=f"Unknown MQTT command: {command}",
        )

    def _handle_http_command(self, command: str, params: Dict) -> CommandResult:
        """Handle HTTP REST device commands."""
        return CommandResult(
            success=True,
            response_code="0x00_SUCCESS",
            message=f"HTTP command executed: {command}",
            data=params,
        )

    def _handle_modbus_command(self, command: str, params: Dict) -> CommandResult:
        """Handle Modbus industrial commands."""
        if command == "read_register":
            return CommandResult(
                success=True,
                response_code="0x00_SUCCESS",
                message="Register read",
                data={"register": params.get("register", 0), "value": 0},
            )
        elif command == "write_register":
            return CommandResult(
                success=True,
                response_code="0x00_SUCCESS",
                message="Register written",
                data=params,
            )
        return CommandResult(
            success=False,
            response_code="0x03_UNKNOWN_CMD",
            message=f"Unknown Modbus command: {command}",
        )

    def _handle_webcam_command(self, command: str, params: Dict) -> CommandResult:
        """Handle local webcam commands."""
        if command == "start_stream":
            return CommandResult(
                success=True,
                response_code="0x00_SUCCESS",
                message="Webcam stream started",
                data={"device_index": self.device.connection_uri},
            )
        return CommandResult(
            success=True,
            response_code="0x00_SUCCESS",
            message=f"Webcam command: {command}",
        )

    @property
    def is_connected(self) -> bool:
        return self._connected


class HardwareBridge:
    """
    The NEVEN Hardware Bridge.

    Manages all device drivers and routes commands to the appropriate hardware.
    Acts as the single entry point for all physical device interactions.
    """

    def __init__(self):
        self._drivers: Dict[str, DeviceDriver] = {}

    def register_device(self, device: Device) -> str:
        """Register a device and create its driver."""
        driver = DeviceDriver(device)
        self._drivers[device.device_id] = driver
        logger.info(f"Device registered in HAL: {device.device_id} ({device.protocol.value})")
        return device.device_id

    def connect_device(self, device_id: str) -> bool:
        """Connect to a registered device."""
        driver = self._drivers.get(device_id)
        if not driver:
            logger.error(f"Device not found: {device_id}")
            return False
        return driver.connect()

    def disconnect_device(self, device_id: str) -> None:
        """Disconnect a device."""
        driver = self._drivers.get(device_id)
        if driver:
            driver.disconnect()

    def execute_command(
        self, device_id: str, command: str, parameters: Dict[str, Any]
    ) -> CommandResult:
        """Execute a command on a specific device."""
        driver = self._drivers.get(device_id)
        if not driver:
            return CommandResult(
                success=False,
                response_code="0x04_NOT_FOUND",
                message=f"Device not found: {device_id}",
            )
        return driver.execute(command, parameters)

    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a device."""
        driver = self._drivers.get(device_id)
        if not driver:
            return None
        return {
            "device_id": device_id,
            "protocol": driver.device.protocol.value,
            "status": driver.status.value,
            "connected": driver.is_connected,
            "connection_uri": driver.device.connection_uri,
        }

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get status of all registered devices."""
        return [
            self.get_device_status(did) for did in self._drivers
        ]

    def connect_all(self) -> Dict[str, bool]:
        """Connect to all registered devices."""
        results = {}
        for device_id in self._drivers:
            results[device_id] = self.connect_device(device_id)
        return results

    def disconnect_all(self) -> None:
        """Disconnect all devices."""
        for device_id in list(self._drivers.keys()):
            self.disconnect_device(device_id)

    @property
    def device_count(self) -> int:
        return len(self._drivers)
