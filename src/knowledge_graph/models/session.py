"""
Session model with temporal boundaries.

Represents experimental sessions with proper temporal constraints.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator
from uuid import uuid4


class Session(BaseModel):
    """
    Session entity representing an experimental recording session.

    Constitutional compliance: Temporal boundary validation enforced.
    """

    session_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique session identifier")
    title: str = Field(..., min_length=1, description="Session title")
    description: Optional[str] = Field(None, description="Session description")
    dataset_id: str = Field(..., description="Parent dataset identifier")
    subject_id: Optional[str] = Field(None, description="Associated subject identifier")

    # Temporal boundaries
    start_time: datetime = Field(..., description="Session start time")
    end_time: Optional[datetime] = Field(None, description="Session end time")
    duration_seconds: Optional[float] = Field(None, description="Session duration in seconds")

    # Device and protocol information
    devices: Dict[str, str] = Field(default_factory=dict, description="Devices used in session")
    protocol_id: Optional[str] = Field(None, description="Associated protocol identifier")

    # Status and metadata
    status: str = Field(default="active", description="Session status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    # Semantic web properties
    rdf_type: str = Field(default="kg:Session", description="RDF type for semantic web")

    @validator('end_time')
    def validate_temporal_boundaries(cls, v, values):
        """
        Constitutional requirement: Proper temporal boundary validation.
        """
        if v is not None and 'start_time' in values:
            start_time = values['start_time']
            if v <= start_time:
                raise ValueError("Session end_time must be after start_time")

            # Check for reasonable duration (not more than 7 days for neuroscience experiments)
            duration = v - start_time
            if duration > timedelta(days=7):
                raise ValueError(
                    f"Session duration exceeds reasonable limits: {duration.days} days. "
                    "Maximum allowed: 7 days."
                )
        return v

    @validator('duration_seconds')
    def validate_duration_consistency(cls, v, values):
        """Validate duration consistency with start/end times."""
        if v is not None and 'start_time' in values and 'end_time' in values:
            start_time = values['start_time']
            end_time = values.get('end_time')

            if end_time is not None:
                calculated_duration = (end_time - start_time).total_seconds()
                if abs(calculated_duration - v) > 1.0:  # Allow 1 second tolerance
                    raise ValueError(
                        f"Duration mismatch: calculated {calculated_duration}s, "
                        f"provided {v}s"
                    )
        return v

    def calculate_duration(self) -> Optional[float]:
        """Calculate session duration in seconds."""
        if self.end_time is not None:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def to_rdf_dict(self) -> Dict[str, Any]:
        """Convert to RDF-compatible dictionary format."""
        return {
            "@id": f"kg:session/{self.session_id}",
            "@type": self.rdf_type,
            "kg:title": self.title,
            "kg:description": self.description,
            "kg:belongsToDataset": f"kg:dataset/{self.dataset_id}",
            "kg:hasSubject": f"kg:subject/{self.subject_id}" if self.subject_id else None,
            "kg:startTime": self.start_time.isoformat(),
            "kg:endTime": self.end_time.isoformat() if self.end_time else None,
            "kg:duration": self.duration_seconds or self.calculate_duration(),
            "kg:usesDevices": [f"kg:device/{device_id}" for device_id in self.devices.keys()],
            "kg:followsProtocol": f"kg:protocol/{self.protocol_id}" if self.protocol_id else None,
            "kg:status": self.status
        }

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }