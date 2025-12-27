import asyncio
import socket
import struct
import time
from typing import Callable

IP_MTU_DISCOVER = 10  # grep -Re IP_MTU_DISCOVER /usr/include/*
IP_PMTUDISC_DO = 2  # grep -Re IP_PMTUDISC_DO /usr/include/*


class MtuTool:
    def __init__(self, host: str, range_start: int, range_stop: int, log_func: Callable[[str], None], timeout=1000):
        self.host = host
        self.range_start = range_start
        self.range_stop = range_stop
        self.log_func = log_func
        self.timeout_ms = timeout

        self.scanning = False
        self.stop_scan = False

    @staticmethod
    async def ping_socket(target, size, timeout) -> tuple[int, str]:
        loop = asyncio.get_running_loop()
        try:
            ip = socket.gethostbyname(target)
        except socket.gaierror as e:
            if e.errno == -2:
                return -3, 'host not found'
            return -1, f'{e=}'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_ICMP)
        sock.setblocking(False)
        sock.setsockopt(socket.IPPROTO_IP, IP_MTU_DISCOVER, IP_PMTUDISC_DO)
        seq = 1
        header = struct.pack('!BBHHH', 8, 0, 0, 0, seq)
        ts = struct.pack('!d', time.perf_counter())
        pad = b'A' * max(0, size - len(ts))
        req = header + ts + pad
        try:
            await loop.sock_sendto(sock, req, (ip, 0))
            data, addr = await asyncio.wait_for(loop.sock_recvfrom(sock, 65535), timeout=timeout)
        except TimeoutError:
            return -5, 'timeout'
        except OSError as e:
            if e.errno == 90:
                return -2, 'should be fragmented'
            return -1, f'{e=}'
        finally:
            sock.close()
        if addr[0] != ip or len(data) < 16:
            return -1, 'unknown'
        icmp_type, icmp_code, _chk, _id, rseq = struct.unpack('!BBHHH', data[:8])
        if icmp_type != 0 or icmp_code != 0 or rseq != seq:
            return -1, 'unknown'
        (t0,) = struct.unpack('!d', data[8:16])
        ms = (time.perf_counter() - t0) * 1000.0
        return ms, f'{ms:.1f}ms'

    def set_stop_scan(self):
        if self.scanning:
            self.stop_scan = True
            return True
        return False

    async def check_fast(self):
        self.scanning = True
        start_time = time.perf_counter()
        fast_search = {'start': self.range_start, 'end': self.range_stop}
        while fast_search['start'] < fast_search['end']:
            if self.stop_scan:
                break
            step = fast_search['end'] - fast_search['start']
            step = int(step / 2)
            if step == 0:
                step = 1
            size_try = fast_search['start'] + step
            reply_time, message = await self.ping_socket(self.host, size_try, self.timeout_ms / 1000)
            yield {
                'Buffer': size_try,
                'Packet': size_try + 28,
                'Info': message,
            }
            print(fast_search['start'], fast_search['end'], step, size_try)
            if reply_time >= 0:
                fast_search['start'] = size_try
                continue
            fast_search['end'] = size_try - 1
        print(fast_search['start'], fast_search['end'])
        self.log_func(f'best MTU ({fast_search["start"]}) {fast_search["start"] + 28}')
        self.scanning = False
        print(time.perf_counter() - start_time)

    async def check_range(self):
        self.scanning = True
        start_time = time.perf_counter()
        last_size = -1
        for i in range(self.range_start, self.range_stop):
            if self.stop_scan:
                break
            reply_time, message = await self.ping_socket(self.host, i, self.timeout_ms / 1000)
            if reply_time >= 0:
                last_size = i
            yield {
                'Buffer': i,
                'Packet': i + 28,
                'Info': message,
            }
        self.log_func(f'best MTU ({last_size}) {last_size + 28}')
        self.scanning = False
        print(time.perf_counter() - start_time)


if __name__ == '__main__':
    mtu_tool = MtuTool('149.112.112.112', 100, 9000, print)


    async def main():
        async for row in mtu_tool.check_fast():
            print(f'Buffer: {row["Buffer"]}, Packet: {row["Packet"]}, Info: {row["Info"]}')


    asyncio.run(main())
