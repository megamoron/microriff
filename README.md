# microriff
A simple Python module to read and write small RIFF files.

Alternatives: For reading you could instead use the more low-level [chunk library](https://docs.python.org/3/library/chunk.html) (deprecated). Although it was originally intended for IFF files, it can be used to parse RIFF files.

## Introduction
It is useful to think of RIFF files as a tree-like data structure. The nodes are called *chunks*. There are two different types of chunks:
- A **regular chunk** contains application data. It consists of:
  - 4-byte name
  - 4-byte little-endian unsigned integer: Specifies the length of the application data
  - Application data

  A padding byte is inserted after a regular chunk if the application data (and thus the entire chunk) is of odd length.

  **Note**: Some parsers expect the padding byte to be a specific value.
- A **container chunk** contains subchunks. It consists of the following fields:
  - 4-byte name: This must be a specific keyword that identifies this chunk as a container (usually `RIFF` or `LIST`)
  - 4-byte little-endian unsigned integer: Equal to the length of the subchunk data plus 4
  - 4-byte alternative name: An alternative name for this container chunk, as the first name-field needs to be a specific keyword.
  - Subchunk data: A sequence of chunks (possibly with associated padding bytes)

A RIFF file consists of a single container chunk named `RIFF`, which usually contains multiple subchunks.

## Installation
Just download the file [`microriff.py`](https://raw.githubusercontent.com/megamoron/microriff/main/microriff.py) and add it to your project. The file is public domain, so no attribution is required.

## Usage

### Parsing
To parse a file, first load it into memory and construct a memoryview of `unsigned char` (format 'B'). Then use the function `parsemem` to parse the root chunk and all of its subchunks. See the [example below](#Reading-and-writing-RIFF-files).

### Working with chunks
You directly access and modify the fields of individual chunks. Regular chunks have the following fields:
- `name` for the 4-byte name (as bytes)
- `data` for the application data (as memoryview of `unsigned char` (format 'B'))

Container chunks have the following fields:
- `name` for the 4-byte name (as bytes)
- `alt_name` for the 4-byte alternative name (as bytes)
- `subchunks` as a list of child chunks

The length field and any padding bytes are added only when the data structure is serialized.

You can refer to children of a container chunk using `__getitem__`. You can either use integer offsets or chunk names (as bytes). You can also the alternative name for children that are themselves containers.

### Writing to a file (or memory)
Each chunk object provides the methods `writefile` and `writemem` to write the subtree rooted at this chunk to a binary file or memoryview of `unsigned char` (format 'B').

## Examples

### Reading and writing RIFF files
Suppose you have a RIFF file 'melon' with a chunk named META. This chunk contains an XML document that you want to edit.

To do this, we first parse the RIFF file and locate the META chunk. Then we run the DOM parser on the application data of this chunk.

```
# Parse the file
with open('melon', 'br') as f:
    memview = memoryview(f.read())
import microriff
root = microriff.parsemem(memview)

# Parse the chunk data
import xml.dom.minidom
dom = xml.dom.minidom.parseString(root[b'META'].data.tobytes())
```
Now we can work with the DOM object. Once we have finished, we write our changes to the META chunk and then save to disk.
```
# Update the chunk data
root[b'META'].data = dom.toxml(encoding='UTF-8')

# Write to file
with open('lemon', 'bw') as f:
    root.writefile(f)
```

### Manually creating and editing a RIFF structure
```
from microriff import RegularChunk, ContainerChunk

# Manually create the tree structure
root = ContainerChunk(b'RIFF', b'JUNK', [
    RegularChunk(b'C0  ', b'Very boring application data.'),
    ContainerChunk(b'RIFF', b'C1  ', [
        RegularChunk(b'C1.0', b'I am a grandchild.'),
        RegularChunk(b'C1.2', b'')
    ])
])

# Modify
root[b'C0  '].data = b'Very interesting application data.'
root[1].name = b'LIST'
e = root[1][1]  # the empty chunk
e.name = b'C1.1'
root[b'C1  '].subchunks.append(RegularChunk(b'C1.2', b'New chunk'))

# Print the RIFF structure (for debugging purposes)
root.print()
```