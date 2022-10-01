
from scipy import signal
import numpy as np
import matplotlib.pyplot as plt

from dfe import DFE
from wireless_mbus_phy_receiver import WMBusPHYReceiver
from telegram_type_a import TelegramTypeA
fs=1.8e6
T = 1 / fs

def read_raw_file():
    floats = np.fromfile('recordings/rec_1.bin', dtype=np.float32)
    iq = floats[::2] + 1j*floats[1::2]
    return iq

def plot_samples(samples):
    plt.plot(np.arange(samples.size), samples, color='r', marker='.', label='samples_raw')
    plt.show()

def add_cfo(signal_in, cfo_hz):
    t = np.arange(0, signal_in.size)*T
    return signal_in * np.exp(1j*2*np.pi*cfo_hz*t)

def main():
    full_file = read_raw_file()
    digital_front_end = DFE()
    digital_front_end.design_low_pass()
    full_file = add_cfo(full_file, cfo_hz=5e3)
    full_file = digital_front_end.low_pass_filter_input(full_file)
    full_file = digital_front_end.quadrature_demodulator(full_file)
    #plot_samples(full_file)

    receiver = WMBusPHYReceiver.create()
    original_signal = full_file
    if original_signal.size % 2 != 0:
        original_signal = original_signal[:original_signal.size-1]
    for subarray in np.split(original_signal, 2):
        receiver.feed_data(subarray)
    dout = receiver.current_frame
    datagram_raw = TelegramTypeA.create_from_bytes(dout)
    datagram_raw.to_file_no_crc('data_out.bin')


if __name__ == '__main__':
    main()

