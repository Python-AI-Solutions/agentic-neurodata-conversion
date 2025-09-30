"""
Enhanced NWB file metadata extraction service.
"""

import pynwb
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class NWBExtractor:
    """Extract detailed metadata from NWB files for knowledge graph."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_full_metadata(self, nwb_path: str) -> Dict[str, Any]:
        """Extract comprehensive metadata from NWB file."""

        self.logger.info(f"Extracting full metadata from {nwb_path}")

        try:
            with pynwb.NWBHDF5IO(nwb_path, 'r') as io:
                nwb_file = io.read()

                metadata = {
                    "session": self._extract_session_metadata(nwb_file),
                    "subject": self._extract_subject_metadata(nwb_file),
                    "institution": self._extract_institution_metadata(nwb_file),
                    "devices": self._extract_devices_metadata(nwb_file),
                    "electrodes": self._extract_electrodes_metadata(nwb_file),
                    "acquisition": self._extract_acquisition_metadata(nwb_file),
                    "trials": self._extract_trials_metadata(nwb_file),
                    "data_summary": self._extract_data_summary(nwb_file)
                }

                self.logger.info("Successfully extracted comprehensive NWB metadata")
                return metadata

        except Exception as e:
            self.logger.error(f"Failed to extract metadata from {nwb_path}: {e}")
            raise

    def _extract_session_metadata(self, nwb_file) -> Dict[str, Any]:
        """Extract session-level metadata."""
        return {
            "session_id": nwb_file.session_id,
            "session_description": nwb_file.session_description,
            "session_start_time": str(nwb_file.session_start_time),
            "timestamps_reference_time": str(nwb_file.timestamps_reference_time),
            "identifier": nwb_file.identifier,
        }

    def _extract_subject_metadata(self, nwb_file) -> Dict[str, Any]:
        """Extract subject metadata."""
        if not nwb_file.subject:
            return {}

        subject_data = {
            "subject_id": nwb_file.subject.subject_id,
            "species": nwb_file.subject.species,
            "sex": nwb_file.subject.sex,
        }

        # Add optional fields if they exist
        optional_fields = ['age', 'weight', 'date_of_birth', 'description']
        for field in optional_fields:
            value = getattr(nwb_file.subject, field, None)
            if value is not None:
                subject_data[field] = str(value)

        return subject_data

    def _extract_institution_metadata(self, nwb_file) -> Dict[str, Any]:
        """Extract institution and lab metadata."""
        data = {}

        if nwb_file.institution:
            data["institution"] = nwb_file.institution
        if nwb_file.lab:
            data["lab"] = nwb_file.lab
        if nwb_file.experimenter:
            data["experimenter"] = str(nwb_file.experimenter)
        if nwb_file.experiment_description:
            data["experiment_description"] = nwb_file.experiment_description

        return data

    def _extract_devices_metadata(self, nwb_file) -> List[Dict[str, Any]]:
        """Extract device information."""
        devices = []

        if nwb_file.devices:
            for name, device in nwb_file.devices.items():
                device_data = {
                    "name": name,
                    "description": device.description,
                }

                # Add manufacturer if available
                if hasattr(device, 'manufacturer') and device.manufacturer:
                    device_data["manufacturer"] = device.manufacturer

                devices.append(device_data)

        return devices

    def _extract_electrodes_metadata(self, nwb_file) -> Dict[str, Any]:
        """Extract electrode configuration metadata."""
        if nwb_file.electrodes is None:
            return {"num_electrodes": 0}

        df = nwb_file.electrodes.to_dataframe()

        metadata = {
            "num_electrodes": len(df),
            "columns": list(df.columns),
        }

        # Extract unique locations and groups
        if 'location' in df.columns:
            metadata["electrode_locations"] = df['location'].unique().tolist()
            metadata["num_locations"] = len(metadata["electrode_locations"])

        if 'group_name' in df.columns:
            metadata["electrode_groups"] = df['group_name'].unique().tolist()
            metadata["num_electrode_groups"] = len(metadata["electrode_groups"])

        # Add electrode groups details
        if nwb_file.electrode_groups:
            groups_detail = []
            for name, group in nwb_file.electrode_groups.items():
                group_data = {
                    "name": name,
                    "description": group.description,
                    "location": group.location,
                    "device_name": group.device.name if group.device else None
                }
                groups_detail.append(group_data)
            metadata["electrode_groups_detail"] = groups_detail

        return metadata

    def _extract_acquisition_metadata(self, nwb_file) -> List[Dict[str, Any]]:
        """Extract acquisition data interfaces metadata."""
        acquisition_data = []

        if nwb_file.acquisition:
            for name, data_interface in nwb_file.acquisition.items():
                interface_data = {
                    "name": name,
                    "type": type(data_interface).__name__,
                    "description": getattr(data_interface, 'description', ''),
                }

                # Add shape and rate information if available
                if hasattr(data_interface, 'data') and hasattr(data_interface.data, 'shape'):
                    interface_data["data_shape"] = list(data_interface.data.shape)

                if hasattr(data_interface, 'rate'):
                    interface_data["sampling_rate"] = float(data_interface.rate)

                acquisition_data.append(interface_data)

        return acquisition_data

    def _extract_trials_metadata(self, nwb_file) -> Dict[str, Any]:
        """Extract trials table metadata."""
        if nwb_file.trials is None:
            return {"num_trials": 0}

        df = nwb_file.trials.to_dataframe()

        metadata = {
            "num_trials": len(df),
            "columns": list(df.columns),
        }

        # Extract unique values for categorical columns
        categorical_columns = ['odorant_id', 'odorant', 'concentration']
        for col in categorical_columns:
            if col in df.columns:
                unique_values = df[col].unique()
                metadata[f"unique_{col}"] = unique_values.tolist()
                metadata[f"num_unique_{col}"] = len(unique_values)

        return metadata

    def _extract_data_summary(self, nwb_file) -> Dict[str, Any]:
        """Extract high-level data summary statistics."""
        return {
            "num_acquisition_interfaces": len(nwb_file.acquisition) if nwb_file.acquisition else 0,
            "num_processing_modules": len(nwb_file.processing) if nwb_file.processing else 0,
            "num_devices": len(nwb_file.devices) if nwb_file.devices else 0,
            "num_electrode_groups": len(nwb_file.electrode_groups) if nwb_file.electrode_groups else 0,
            "has_units": nwb_file.units is not None and len(nwb_file.units) > 0,
            "has_trials": nwb_file.trials is not None and len(nwb_file.trials) > 0,
            "has_subject": nwb_file.subject is not None,
        }

    def create_semantic_triples(self, metadata: Dict[str, Any], dataset_uri: str) -> List[tuple]:
        """Convert extracted metadata to semantic triples for knowledge graph."""

        triples = []

        # Session triples
        session_data = metadata.get("session", {})
        for key, value in session_data.items():
            if value:
                predicate = f"http://knowledge-graph.org/ontology/{key}"
                triples.append((dataset_uri, predicate, str(value)))

        # Subject triples
        subject_data = metadata.get("subject", {})
        if subject_data:
            subject_uri = f"{dataset_uri}/subject"
            triples.append((dataset_uri, "http://knowledge-graph.org/ontology/hasSubject", subject_uri))
            triples.append((subject_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://knowledge-graph.org/ontology/Subject"))

            for key, value in subject_data.items():
                predicate = f"http://knowledge-graph.org/ontology/{key}"
                triples.append((subject_uri, predicate, str(value)))

        # Institution triples
        institution_data = metadata.get("institution", {})
        for key, value in institution_data.items():
            if value:
                predicate = f"http://knowledge-graph.org/ontology/{key}"
                triples.append((dataset_uri, predicate, str(value)))

        # Devices triples
        devices = metadata.get("devices", [])
        for i, device in enumerate(devices):
            device_uri = f"{dataset_uri}/device/{device['name']}"
            triples.append((dataset_uri, "http://knowledge-graph.org/ontology/hasDevice", device_uri))
            triples.append((device_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://knowledge-graph.org/ontology/Device"))

            for key, value in device.items():
                if value:
                    predicate = f"http://knowledge-graph.org/ontology/{key}"
                    triples.append((device_uri, predicate, str(value)))

        # Electrodes summary triples
        electrodes_data = metadata.get("electrodes", {})
        for key, value in electrodes_data.items():
            if value is not None and key not in ['electrode_groups_detail']:
                predicate = f"http://knowledge-graph.org/ontology/{key}"
                if isinstance(value, list):
                    value = json.dumps(value)
                triples.append((dataset_uri, predicate, str(value)))

        # Acquisition data triples
        acquisition_data = metadata.get("acquisition", [])
        for i, interface in enumerate(acquisition_data):
            interface_uri = f"{dataset_uri}/acquisition/{interface['name']}"
            triples.append((dataset_uri, "http://knowledge-graph.org/ontology/hasAcquisitionInterface", interface_uri))
            triples.append((interface_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://knowledge-graph.org/ontology/AcquisitionInterface"))

            for key, value in interface.items():
                if value is not None:
                    predicate = f"http://knowledge-graph.org/ontology/{key}"
                    if isinstance(value, list):
                        value = json.dumps(value)
                    triples.append((interface_uri, predicate, str(value)))

        # Trials summary triples
        trials_data = metadata.get("trials", {})
        for key, value in trials_data.items():
            if value is not None:
                predicate = f"http://knowledge-graph.org/ontology/{key}"
                if isinstance(value, list):
                    value = json.dumps(value)
                triples.append((dataset_uri, predicate, str(value)))

        # Data summary triples
        summary_data = metadata.get("data_summary", {})
        for key, value in summary_data.items():
            if value is not None:
                predicate = f"http://knowledge-graph.org/ontology/{key}"
                triples.append((dataset_uri, predicate, str(value)))

        return triples