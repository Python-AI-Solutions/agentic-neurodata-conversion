# src/<lab_slug>/converter.py (auto-generated)

from neuroconv import NWBConverter


def build_converter_class(class_name: str, interface_spec: dict[str, dict[str, str]]):
    """
    interface_spec: {
      "Ephys": {"class": "neuroconv.datainterfaces.SpikeGLXRecordingInterface",
                "argmap": {"folder_path": "/raw/animal/session/ephys"}},
      "Behavior": {"class": "neuroconv.datainterfaces.DeepLabCutInterface",
                   "argmap": {"file_path": "/raw/animal/session/behavior/poses.csv"}},
      ...
    }
    """
    # Dynamically import classes
    data_interface_classes: dict[str, type] = {}
    for key, spec in interface_spec.items():
        mod, clsname = spec["class"].rsplit(".", 1)
        mod = __import__(mod, fromlist=[clsname])
        data_interface_classes[key] = getattr(mod, clsname)

    # Create subclass type
    return type(
        class_name, (NWBConverter,), {"data_interface_classes": data_interface_classes}
    )
