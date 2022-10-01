import scipy
import numpy as np


class DFE:
    FS = 1.8e6

    def design_low_pass(self):
        self.low_pass_h = scipy.signal.firwin(81, 150e3, width=25e3, fs=self.FS)

    def low_pass_filter_input(self, data_in):
        return scipy.signal.convolve(data_in, self.low_pass_h)

    def quadrature_demodulator(self, data_in):
        conjugate = np.conjugate(np.roll(data_in, 1))
        product = data_in[1:] * conjugate[1:]
        return np.angle(product, )
