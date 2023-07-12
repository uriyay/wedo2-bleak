# wedo2-bleak
Bringing [wedo2](https://pypi.org/project/wedo2/) pythonic module to Windows by using [bleak](https://pypi.org/project/bleak/) instead of [pygatt](https://pypi.org/project/pygatt/)

## Summary
This is a wrapper for [wedo2](https://pypi.org/project/wedo2/) that replaces the backend with backends.BleakBackend instead of _Patched_BGAPIBackend.
backends is copied from [here](https://github.com/xloem/muse-lsl/blob/cbb43ce4c566b6c96f8846afaf2d2a7c5eef6460/muselsl/backends.py) thanks to [xloem](https://github.com/xloem), with some modifications that were needed for supporting wedo2.

## Usage
Turn on the wedo2 hub and run:
```python
import wedo2_hub_wrapper
hub = wedo2_hub_wrapper.get_wedo2_hub()
```

## Installation
```
python -m pip install -r requirements.txt
python setup.py install
```