import asyncio
import atexit
import time
import bleak

def _wait(coroutine):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coroutine)

def sleep(seconds):
    time.sleep(seconds)

class BleakBackend:
    def __init__(self, device_name=None):
        '''
        @param device_name: filter by device name, not just by the smallest distance
        '''
        self.connected = set()
        atexit.register(self.stop)
        # run the event loop when sleeping
        global sleep
        sleep = self.pump
        self.device_name = device_name

    def start(self):
        pass

    def pump(self, seconds=1):
        _wait(asyncio.sleep(seconds))

    def stop(self):
        for device in [*self.connected]:
            device.disconnect()

    def scan(self, timeout=10):
        if isinstance(bleak, ModuleNotFoundError):
            raise bleak
        scanner = bleak.BleakScanner()
        devices = _wait(scanner.discover(timeout))
        results = []
        for device in devices:
            if self.device_name and device.name != self.device_name:
                continue
            #device.rssi is deprecated, so use device.details.adv.raw_signal_strength_in_d_bm instead
            results.append(dict(name=device.name,
                address=device.address,
                rssi=device.details.adv.raw_signal_strength_in_d_bm
            ))
        return results
    
    def connect(self, address):
        result = BleakDevice(self, address)
        result.connect()
        return result

class BleakDevice:
    def __init__(self, adapter, address):
        self._adapter = adapter
        self._client = bleak.BleakClient(address)

    def connect(self):
        _wait(self._client.connect())
        self._adapter.connected.add(self)

    def disconnect(self):
        _wait(self._client.disconnect())
        self._adapter.connected.remove(self)

    def char_write_handle(self, value_handle, value, wait_for_response=True, timeout=30):
        _wait(self._client.write_gatt_char(
            value_handle,
            bytearray(value),
            wait_for_response))
        
    def char_write(self, char_uuid, data):
        _wait(self._client.write_gatt_char(char_uuid, data))

    def char_read(self, char_uuid):
        return _wait(self._client.read_gatt_char(char_uuid))
        
    def subscribe(self, uuid, callback=None, indication=False, wait_for_response=True):
        def wrap(value_handle, data):
            callback(value_handle, data)
        _wait(self._client.start_notify(uuid, wrap))
        
        # force sleepy wait for 6 services, because wedo2's ServiceManager waits only for service 6
        # but there is another service with the number 2 that comes afterwards (also, might not receiving in the right order)
        # another problem is that ServiceManager waits by using a busy loop which affects the ability of bleak to run in parallel
        while len(list(callback.__self__.services_data.keys())) < 6:
                #use asyncio.sleep and not time.sleep because the second one is blocking
                _wait(asyncio.sleep(0.1))

    def unsubscribe(self, uuid):
        _wait(self._client.stop_notify(uuid))
