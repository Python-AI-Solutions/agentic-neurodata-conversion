# tools/interface_registry.py
import importlib
import inspect


def discover_neuroconv_interfaces():
    ndi = importlib.import_module("neuroconv.datainterfaces")
    registry = {}
    for name in dir(ndi):
        if name.endswith("Interface"):
            cls = getattr(ndi, name)
            if inspect.isclass(cls):
                init = inspect.signature(cls.__init__)
                params = [p for p in init.parameters if p != "self"]
                registry[name] = {
                    "qualified_name": f"neuroconv.datainterfaces.{name}",
                    "init_params": params,
                    "doc": (inspect.getdoc(cls) or "").split("\n")[0],
                }
    return registry


if __name__ == "__main__":
    import json

    print(json.dumps(discover_neuroconv_interfaces(), indent=2))
