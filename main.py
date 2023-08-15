import subprocess


def ping_with_df(target, size):
    command = ['ping', '-f', '-l', str(size), '-n', '1', target]

    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        output = output.decode('utf-8', 'ignore')
        # print(output)
        ms = output[:output.find('ms')]
        ms = ms[ms.rfind('=') + 1:]
        return int(ms)
    except subprocess.CalledProcessError as e:
        output = e.output.decode('utf-8', 'ignore')
        if 'Paket msste fragmentiert werden, DF-Flag ist jedoch gesetzt.' in output:
            return -2
        print("error:", output)
        return -1


if __name__ == '__main__':
    for i in range(1300, 1500):
        time = ping_with_df('8.8.8.8', i)
        if time >= 0:
            print(i, i + 28, f'{time}ms')
        elif time == -2:
            print(i, i + 28, 'should be fragmented')
