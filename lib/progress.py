from __future__ import division

import os
import bz2
import time

import xbmc, xbmcgui

from script_exceptions import Canceled, WriteError, DecompressError
from utils import size_fmt

class FileProgress(xbmcgui.DialogProgress):
    """Extends DialogProgress as a context manager to
       handle the file progress"""

    BLOCK_SIZE = 131072

    def __init__(self, heading, infile, outpath, size):
        xbmcgui.DialogProgress.__init__(self)
        self.create(heading, outpath, size_fmt(size))
        self._size = size
        self._in_f = infile
        try:
            self._out_f = open(outpath, 'wb')
        except IOError as e:
            raise WriteError(e)
        self._outpath = outpath
        self._done = 0
 
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._in_f.close()
        self._out_f.close()
        self.close()

        # If an exception occurred remove the incomplete file.
        if exc_type is not None:
            os.remove(self._outpath)

    def start(self):
        start_time = time.time()
        while self._done < self._size:
            if self.iscanceled():
                raise Canceled
            data = self._read()
            try:
                self._out_f.write(data)
            except IOError as e:
                raise WriteError(e)
            percent = int(self._done * 100 / self._size)
            bytes_per_second = self._done / (time.time() - start_time)
            self.update(percent, line3="{0}/s".format(size_fmt(bytes_per_second)))

    def _getdata(self):
        return self._in_f.read(self.BLOCK_SIZE)

    def _read(self):
        data = self._getdata()
        self._done += len(data)
        return data


class DecompressProgress(FileProgress):
    decompressor = bz2.BZ2Decompressor()
    def _read(self):
        data = self._getdata()
        try:
            decompressed_data = self.decompressor.decompress(data)
        except IOError as e:
            raise DecompressError(e)
        self._done = self._in_f.tell()
        return decompressed_data
    

def restart_countdown(message, timeout=10):
    progress = xbmcgui.DialogProgress()
    progress.create('Rebooting')
        
    restart = True
    seconds = timeout
    while seconds >= 0:
        progress.update(int((timeout - seconds) / timeout * 100),
                        message,
                        "Rebooting{}{}...".format((seconds > 0) * " in {} second".format(seconds),
                                                  "s" * (seconds > 1)))
        xbmc.sleep(1000)
        if progress.iscanceled():
            restart = False
            break
        seconds -= 1
    progress.close()

    return restart
