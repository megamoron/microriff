'A simple Python module to read and write small RIFF files.'

CONTAINER_KEYWORDS = (
    # list of chunk names that identify a chunk as container
    b'RIFF',
    b'LIST'
)

PADDING = b'0'  # 0x30

def parsemem(mem):
    '''
    Parses a chunk stored in mem, possibly recursively.
    Any additional data after the chunk is ignored.

    mem: memoryview (of format 'B') to parse
    returns the root chunk (either RegularChunk or ContainerChunk)
    '''
    name = mem[0:4].tobytes()
    end = mem[4:8].cast('I')[0] + 8
    if name in CONTAINER_KEYWORDS:
        alt_name = mem[8:12].tobytes()
        subchunks = []
        offset = 12
        while offset < end:
            chunk = parsemem(mem[offset:])
            subchunks.append(chunk)
            offset += chunk.size()
        return ContainerChunk(name, alt_name, subchunks)
    else:
        return RegularChunk(name, mem[8:end])


class RegularChunk:
    'Represents a container chunk. The length field and padding are handled automatically.'
    def __init__(self, name, data):
        '''
        name: name of the chunk (4 bytes)
        data: binary sequence type (ie. application data)
        '''
        assert len(name) == 4
        assert name not in CONTAINER_KEYWORDS
        self.name = name
        self.data = data

    def size(self):
        'Gets the size of the chunk (including headers and padding)'
        if len(self.data) % 2 == 0:
            return 8 + len(self.data)
        else:
            return 8 + len(self.data) + 1

    def writemem(self, mem=None):
        '''
        mem: memoryview (of format 'B') to write the chunks to
        returns the memoryview of the chunk just written (including any padding)
        '''
        size = self.size()
        if mem is None:
            mem = memoryview(bytearray(size))
        else:
            mem = mem[0:size]
        mem[0:4] = self.name
        mem[4:8] = len(self.data).to_bytes(length=4, byteorder='little', signed=False)
        mem[8:8+len(self.data)] = self.data
        if len(self.data) % 2 == 1:
            mem[8+len(self.data)] = ord(PADDING)
        return mem

    def writefile(self, file):
        '''
        file: binary file to write the chunks to
        '''
        file.write(self.name)
        file.write(len(self.data).to_bytes(length=4, byteorder='little', signed=False))
        file.write(self.data)
        if len(self.data) % 2 == 1:
            file.write(PADDING)

    def __repr__(self, spaces=0):
        'Returns a non-reconstructible representation (for debugging purposes)'
        import hashlib
        hash = hashlib.md5(self.data).hexdigest()
        if len(self.data) % 2 == 0:
            return spaces*' ' + f'{self.name}, {len(self.data)}, data (md5: {hash})\n'
        else:
            return spaces*' ' + f'{self.name}, {len(self.data)}, data (md5: {hash}), padding\n'


class ContainerChunk:
    'Represents a container chunk. The length field is automatically computed when writing.'
    def __init__(self, name, alt_name, subchunks):
        '''
        name: name of the chunk, must be a container keyword (4 bytes)
        alt_name: alternative name for this container chunk (4 bytes)
        subchunks: a list of subchunks
        '''
        assert name in CONTAINER_KEYWORDS
        assert len(name) == 4
        self.name = name
        self.alt_name = alt_name
        self.subchunks = subchunks

    def __getitem__(self, key):
        '''
        You can refer to subchunks either by index, or by (binary) name.
        You can use the alernative name to refer to a container chunk.
        '''
        if isinstance(key, int):
            return self.subchunks[key]
        if isinstance(key, bytes):
            for chunk in self.subchunks:
                if chunk.name == key:
                    return chunk
                if isinstance(chunk, ContainerChunk) and chunk.alt_name == key:
                    return chunk
            raise KeyError(key)
        raise TypeError("Type of subscription key must either be 'int' or 'bytes'")

    def size(self):
        'Gets the size of the chunk (including headers and padding)'
        return 12 + sum([chunk.size() for chunk in self.subchunks])

    def writemem(self, mem=None):
        '''
        mem: memoryview (of format 'B') to write the chunks and subchunks to
        returns the memoryview of the chunks just written
        '''
        size = self.size()
        if mem is None:
            mem = memoryview(bytearray(size))
        else:
            mem = mem[0:size]
        mem[0:4] = self.name
        mem[4:8] = (size-8).to_bytes(length=4, byteorder='little', signed=False)
        mem[8:12] = self.alt_name
        offset = 12
        for chunk in self.subchunks:
            chunk.writemem(mem[offset:])
            offset += chunk.size()
        return mem

    def writefile(self, file):
        '''
        file: binary file to write the chunks and subchunks to
        '''
        file.write(self.name)
        length = 4 + sum([chunk.size() for chunk in self.subchunks])
        file.write(length.to_bytes(length=4, byteorder='little', signed=False))
        file.write(self.alt_name)
        for chunk in self.subchunks:
            chunk.writefile(file)

    def __repr__(self, spaces=0):
        'Returns a non-reconstructible representation (for debugging purposes)'
        length = 4 + sum([chunk.size() for chunk in self.subchunks])
        ret = spaces*' ' + f'{self.name}, {length}, {self.alt_name}\n'
        for chunk in self.subchunks:
            ret += chunk.__repr__(spaces+4)
        return ret


def _printpads(mem):
    '''
    Parses a chunk stored in mem, possibly recursively, and prints all padding values.
    Any additional data after the chunk is ignored.
    For debugging purposes

    mem: memoryview (of format 'B') to parse
    '''
    name = mem[0:4].tobytes()
    end = mem[4:8].cast('I')[0] + 8
    if name in CONTAINER_KEYWORDS:
        offset = 12
        while offset < end:
            _printpads(mem[offset:])
            offset += mem[offset+4:offset+8].cast('I')[0] + 8
            offset += offset % 2  # Consume padding if present (i.e. if offset is now odd)
    else:
        if end % 2 == 1:
            pad = mem[end].to_bytes(1, 'little')
            print(f'Chunk {name} has padding {pad}')
