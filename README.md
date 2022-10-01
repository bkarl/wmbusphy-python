# wmbusphy-python
Receiver for Wireless M-Bus (EN 13757-4) written in Python.
This receiver will synchronize to an incomming WMBus packet using a correlation based approach and output all bits inside the packet.

Further processing can be done using additional tools like [wmbusmeters](https://github.com/weetmuts/wmbusmeters).

# Usage
See the script "process_recording.py". A recording is passed to the receiver in several parts and the resulting raw data is written to a file after stripping the.
The CRC is stripped because the file can be analyzed by wmbusmeters using
<code> 
wmbusmeters --analyze data_out.bin
</code>


# Limitations
For now the code has only been tested with recordings, and a proper frame detection is missing.