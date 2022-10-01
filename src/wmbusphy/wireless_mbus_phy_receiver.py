import numpy as np
import attrs
from scipy import signal
import matplotlib.pyplot as plt
from telegram_type_a import TelegramTypeA

@attrs.define
class WMBusPHYReceiver:

    oversampled_preamble: np.ndarray
    oversampling: int = 18 # must be even
    ThreeOfSixCode = {
        22: 0,
        13: 1,
        14: 2,
        11: 3,
        28: 4,
        25: 5,
        26: 6,
        19: 7,
        44: 8,
        37: 9,
        38: 10,
        35: 11,
        52: 12,
        49: 13,
        50: 14,
        41: 15
    }
    sampling_point: int = -1
    frame_len_bytes: int = 0
    bytes_received: int = 0
    sof_detected: bool = False
    frame_done: bool = False
    current_frame: bytes = b''
    spilled_bits: np.ndarray = np.array([])
    spilled_nibbles: np.ndarray = np.array([])
    plot_for_debugging: bool = False
    preamble_bits = [-1] + [-1, 1] * 19 + [-1] * 4 + [1] * 4 + [-1, 1] # 0 is encoded as -1 because of quadrature demodulator

    @classmethod
    def create(cls, oversampling=18):
        preamble = WMBusPHYReceiver.gen_preamble(oversampling)
        return cls(oversampling=oversampling, oversampled_preamble=preamble)

    def feed_data(self, din):
        if self.frame_done:
            self.reset_receiver()

        if self.sampling_point < 0:
            self.find_start_of_frame(din)
        self.recover_data(din)

    def reset_receiver(self):
        self.sampling_point = -1
        self.frame_done = False
        self.current_frame = b''

    def find_start_of_frame(self, din):
        corr = signal.correlate(din, self.oversampled_preamble)
        self.sampling_point = np.where(corr == np.max(corr))[0][0]
        self.sampling_point += (self.oversampling // 2)

        if not self.plot_for_debugging:
            return

        figure, axis = plt.subplots(2, 1)
        x = np.arange(corr.shape[0])
        axis[0].plot(x, corr, label='corr')
        axis[0].set_title("Correlation Metric")
        sof = np.where(corr == np.max(corr))[0][0]
        X = np.arange(din.size)
        corr_stuffed = np.zeros(X.size)
        corr_stuffed[sof - self.oversampled_preamble.shape[0]: sof] = self.oversampled_preamble
        axis[1].set_title("RX signal and preamble")
        axis[1].plot(X, corr_stuffed, color='b', label='samples_raw')
        axis[1].plot(X, din, color='r', marker='.', label='samples_raw')
        plt.show()

    @staticmethod
    def gen_preamble(oversampling):
        oversampled_preamble = np.zeros((len(WMBusPHYReceiver.preamble_bits) * oversampling))
        for idx, bit in enumerate(WMBusPHYReceiver.preamble_bits):
            oversampled_preamble[idx * oversampling:(idx + 1) * oversampling] = bit * 1
        return oversampled_preamble

    def recover_data(self, raw_samples):
        bits = self.sample_and_demodulate(raw_samples)
        data = self.decode_line_coding(bits)

        if self.frame_len_bytes == 0:
            self.frame_len_bytes = TelegramTypeA.calc_real_frame_size(data[0])

        self.calc_new_sample_offset(raw_samples)
        self.current_frame += data.tobytes()
        self.current_frame = self.correct_frame_size(self.current_frame)

    def correct_frame_size(self, data):
        if len(data) >= self.frame_len_bytes:
            data = data[:self.frame_len_bytes]
            self.frame_done = True
        return data

    def calc_new_sample_offset(self, raw_samples):
        L = raw_samples.size - self.sampling_point - (self.oversampling // 2)
        self.sampling_point = int((np.ceil(L / self.oversampling) * self.oversampling) - L)
        self.sampling_point += (self.oversampling // 2)
        self.sampling_point = self.sampling_point % self.oversampling

    def decode_line_coding(self, bits):
        bits = np.insert(bits, 0, self.spilled_bits) # prepend the bits that have been spilled in the last cycle
        self.spilled_bits, bits = self.save_spilled_data_for_next_decoding_step(bits, 6) # truncate data and safe spilled bits for next cycle
        bits = bits.reshape((bits.shape[0] // 6, 6))  # group 6 bits together to decode line code later on
        nibbles = bits.dot(2 ** np.arange(6)[::-1])  # make 6 bits wide word from the individual bits
        nibbles = nibbles.astype(np.uint8)
        nibbles = np.insert(nibbles, 0, self.spilled_nibbles) # prepend the nibbles that have been spilled in the last cycle
        self.spilled_nibbles, nibbles = self.save_spilled_data_for_next_decoding_step(nibbles, 2)

        for key in self.ThreeOfSixCode: # the actual decoding
            nibbles[np.where(nibbles == key)] = self.ThreeOfSixCode[key]

        data = nibbles[0::2] << 4
        data |= nibbles[1::2]
        return data

    def save_spilled_data_for_next_decoding_step(self, data_in, max_intake):
        spilled_data_out = np.array([])
        truncated_data = data_in
        if data_in.size % max_intake != 0:
            spilled_data_out = data_in[data_in.size - (data_in.size % max_intake):]
            truncated_data = data_in[:data_in.size - (data_in.size % max_intake)]
        return spilled_data_out, truncated_data

    def sample_and_demodulate(self, raw_samples):
        bits = raw_samples[self.sampling_point::self.oversampling]
        bits[np.where(bits > 0)] = 1
        bits[np.where(bits <= 0)] = 0
        return bits