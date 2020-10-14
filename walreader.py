import struct
from ctypes import *
from typing import IO, BinaryIO, Union, List, Dict, Tuple, Set, Union, Any, TypeVar
from pathlib import Path
import logging

log = logging.getLogger(__name__)

class _WALFileHeader(BigEndianStructure):
    _fields_ = [
        ('Signature', c_uint32),
        ('Version', c_uint32),
        ('PageSize', c_uint32),
        ('SequenceNumber', c_uint32),
        ('Salt1', c_uint32),
        ('Salt2', c_uint32),
        ('CheckSum1', c_uint32),
        ('Checksum2', c_uint32)
    ]

class _WALFrameHeader(BigEndianStructure):
    _fields_ = [
        ('DBPageNumber', c_uint32),
        ('EndofTransaction', c_uint32),
        ('Salt1', c_uint32),
        ('Salt2', c_uint32),
        ('Checksum1', c_uint32),
        ('Checksum2', c_uint32)
    ]

def _memcpy(buf, fmt):
    return cast(c_char_p(buf), POINTER(fmt)).contents

class WAL():
    # fhandle: BinaryIO
    fbuf: bytes
    fileheader: bytes
    pagesize: int = 0
    count: int = 0

    def open(self, filepath: Union[str, Path])-> bytes:
        with open(filepath, 'rb') as f:
            self.fbuf = f.read()
        self.read_file_header()
        return self.fbuf
    
    def read_file_header(self)-> None:
        self.fileheader = _memcpy(self.fbuf[:sizeof(_WALFileHeader)], _WALFileHeader)
        # checking file signature
        if self.fileheader.Signature not in (0x377f0682, 0x377f0683):
            logging.error("Invalid File Format")
            return
        self.pagesize = self.fileheader.PageSize
        self.cpseqnum = self.fileheader.SequenceNumber

    def get_frames(self)-> None:
        self.frame_list = []
        frame_buf = self.fbuf[sizeof(_WALFileHeader):]
        for offset in range(0, len(frame_buf), self.pagesize + sizeof(_WALFrameHeader)):
            frame_element = []
            frameheader = _memcpy(frame_buf[offset : offset+sizeof(_WALFrameHeader)], _WALFrameHeader)
            frame_element.append(frameheader)
            framebody = frame_buf[offset+sizeof(_WALFrameHeader) : offset+sizeof(_WALFrameHeader)+self.pagesize]
            frame_element.append(framebody)
            self.frame_list.append(frame_element)
    


        

        