import os

STDIN = 0
STDOUT = 1
STDERR = 2

frame_size = 4096*1024

def read_file(path):
    assert isinstance(path, str)
    fd = os.open(path, os.O_RDONLY, 0777)
    try:
        data = ""
        frame = os.read(fd, frame_size)
        while frame != "":
            data += frame
            frame = os.read(fd, frame_size)
    finally:
        os.close(fd)
    return data.decode('utf-8')

def write(fd, message):
    assert isinstance(message, unicode)
    os.write(fd, message.encode('utf-8'))
