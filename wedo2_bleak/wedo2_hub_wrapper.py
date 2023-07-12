import wedo2_bleak.backends as backends
from wedo2 import smarthub

WEDO2_DEVICE_NAME = 'LPF2 Smart Hub'

def get_wedo2_hub():
    '''
    This function returns wedo2 hub while using BleakBackend instead of pygatt's BGAPI backend
    Make sure to turn the wedo2 hub on first
    '''
    smarthub.adapter = backends.BleakBackend(WEDO2_DEVICE_NAME)
    hub = smarthub.Smarthub()
    return hub