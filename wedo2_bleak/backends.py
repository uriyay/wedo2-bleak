import asyncio
import atexit
import time
import bleak

QUEUE_SIZE = 100

class ErrorQueueFull(Exception):
    pass

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
        self.connected.add(result)
        return result
    
class CharReader:
    def __init__(self, char_uuid):
        self.char_uuid = char_uuid
        #the queue must be limited by a certain size
        self.queue = asyncio.Queue(QUEUE_SIZE)
        self.latest_result = None

    def queue_put(self, data):
        try:
            self.queue.put_nowait(data)
        except asyncio.QueueFull as e:
            for i in QUEUE_SIZE:
                _ = self.queue_get()
                try:
                    self.queue.put_nowait(data)
                except asyncio.QueueFull:
                    pass
            else:
                #something is wrong, must be a high sampling rate
                raise ErrorQueueFull(f"when handling char uuid = {self.char_uuid}")

    def queue_get(self, timeout=0.1):
        try:
            result = _wait(asyncio.wait_for(self.queue.get(), timeout))
            self.latest_result = result
        except asyncio.TimeoutError:
            return b''
        
    def queue_get_latest(self, timeout=0.1):
        '''
        get the most latest update (based on bgapi behaviour)
        '''
        result = None
        while True:
            cur = self.queue_get(timeout)
            if cur == b'':
                if self.latest_result is not None:
                    #prefer data instead of no data (which is caused by a timeout)
                    result = self.latest_result
                else:
                    result = cur
                #either way, we got to the end of the queue
                break
        return result

    def __call__(self, handle, data):
        if handle.uuid == self.char_uuid:
            self.queue_put(data)

class BleakDevice:
    def __init__(self, adapter, address):
        self._adapter = adapter
        self._client = bleak.BleakClient(address)
        self.char_readers = []

    def __del__(self):
        self.disconnect()

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
        char_uuid = char_uuid.lower()
        char_reader = None
        for cr in self.char_readers:
            if cr.char_uuid == char_uuid:
                char_reader = cr
                break
        else:
            #create a new one
            char_reader = CharReader(char_uuid=char_uuid)
            self.subscribe(char_uuid, char_reader)
            self.char_readers.append(char_reader)

        result = char_reader.queue_get_latest()
        return result
        
    def subscribe(self, uuid, callback=None, indication=False, wait_for_response=True):
        def wrap(value_handle, data):
            callback(value_handle, data)
        _wait(self._client.start_notify(uuid, wrap))
        
        # force sleepy wait for 6 services, because wedo2's ServiceManager waits only for service 6
        # but there is another service with the number 2 that comes afterwards (also, might not receiving in the right order)
        # another problem is that ServiceManager waits by using a busy loop which affects the ability of bleak to run in parallel
        if hasattr(callback, '__self__') and hasattr(callback.__self__, 'services_data'):
            while len(list(callback.__self__.services_data.keys())) < 6:
                #use asyncio.sleep and not time.sleep because the second one is blocking
                _wait(asyncio.sleep(0.1))

    def unsubscribe(self, uuid):
        _wait(self._client.stop_notify(uuid))

    def sleep(self, interval):
        self._adapter.pump(interval)