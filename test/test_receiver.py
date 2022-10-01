import struct
import unittest
from unittest import mock
from unittest.mock import patch

import numpy as np

from wireless_mbus_phy_receiver import WMBusPHYReceiver


class TestWMBusPHYReceiver(unittest.TestCase):
    def setUp(self):
        self.receiver = WMBusPHYReceiver.create()
        self.receiver.plot_for_debugging = False
        self.receiver.correlation_metric_treshold = 0

    @patch('wireless_mbus_phy_receiver.WMBusPHYReceiver.gen_preamble')
    def test_create_and_parameters_set(self, gen_preamble_mock):
        receiver = WMBusPHYReceiver.create(oversampling=32)
        assert receiver.oversampling == 32
        assert receiver.frame_len_bytes == 0
        assert receiver.sampling_point == -1
        assert receiver.sof_detected is False
        assert receiver.frame_done is False
        assert receiver.current_frame == b''
        gen_preamble_mock.assert_called_once_with(32)

    @patch('wireless_mbus_phy_receiver.WMBusPHYReceiver.find_start_of_frame')
    @patch('wireless_mbus_phy_receiver.WMBusPHYReceiver.recover_data')
    def test_feed_data_find_sof(self, recover_data_mock, find_start_of_frame_mock):
        din = np.arange(10)
        self.receiver.feed_data(din)
        find_start_of_frame_mock.assert_called_once_with(din)
        recover_data_mock.assert_called_once_with(din)

    @patch('wireless_mbus_phy_receiver.WMBusPHYReceiver.find_start_of_frame')
    @patch('wireless_mbus_phy_receiver.WMBusPHYReceiver.recover_data')
    def test_feed_data_sof_known(self, recover_data_mock, find_start_of_frame_mock):
        din = np.arange(10)
        self.receiver.sampling_point = 1
        self.receiver.feed_data(din)
        find_start_of_frame_mock.assert_not_called()
        recover_data_mock.assert_called_once_with(din)

    def test_gen_preamble(self):
        bits = [-1,1]
        os = 4
        WMBusPHYReceiver.preamble_bits = bits
        preamble_out = WMBusPHYReceiver.gen_preamble(os)
        np.testing.assert_array_equal(preamble_out, [-1, -1, -1, -1, 1, 1, 1, 1])

    def test_find_start_of_frame(self):
        self.receiver.oversampled_preamble = np.array([0, 0, 0, 0, 1, 0, 0, 0, 0])
        din = np.array([1, 0, 0, 0, 0])
        self.receiver.oversampling = 2
        self.receiver.find_start_of_frame(din)
        assert self.receiver.sampling_point == 4 + 1

    def test_sample_and_demodulate(self):
        sym_in = np.array([-0.25, -0.5, -0.7, 1.5, 0.5, 0.25, 0, -0.3])
        bits_out_expected = np.array([0, 1, 1, 0])
        self.receiver.sampling_point = 1
        self.receiver.oversampling = 2
        bits_out = self.receiver.sample_and_demodulate(sym_in)
        np.testing.assert_array_equal(bits_out, bits_out_expected)

    def test_decode_line_coding(self):
        bits_in = np.array([1, 0, 0, 0, 1, 1,  #35
                            0, 1, 1, 1, 0, 0,  #28
                            1, 1, 1, 1, 1, 1,  #one symbol to much (needs to be even) and will be removed
                            1, 1])             #truncated symbol

        bytes_out = self.receiver.decode_line_coding(bits_in)
        np.testing.assert_array_equal(bytes_out, np.array([0xB4]))


    def test_calc_new_sample_offset(self):
        #(block_len, first sampling point, distance, expected result)
        test_params = [(8, 2, 2, 0), #__X_X_X_|X_X_X_X_
                       (8, 3, 2 ,1)] #___X_X_X|_X_X_X_X
        for tp in test_params:
            with self.subTest(tp=tp):
                N, s, k, expected_sampling_point = tp

                din = np.zeros((N))
                self.receiver.sampling_point = s
                self.receiver.oversampling = k
                self.receiver.calc_new_sample_offset(din)
                assert self.receiver.sampling_point == expected_sampling_point

    def test_correct_frame_size_first_frame(self):
        self.receiver.bytes_received = 10
        self.receiver.frame_len_bytes = 15
        data_in = np.arange(10)
        data_out = self.receiver.correct_frame_size(data_in)
        np.testing.assert_array_equal(data_in, data_out)

    def test_correct_frame_size_frame_done(self):
        self.receiver.bytes_received = 20
        self.receiver.frame_len_bytes = 15
        data_in = np.arange(20)
        data_out = self.receiver.correct_frame_size(data_in)
        np.testing.assert_array_equal(data_in[:15], data_out)

    def test_save_spilled_data_for_next_decoding_step(self):
        data_in = np.arange(17)
        spilled_data_out, truncated_data = self.receiver.save_spilled_data_for_next_decoding_step(data_in, 16)
        np.testing.assert_array_equal(truncated_data, np.arange(16))
        np.testing.assert_array_equal(spilled_data_out, np.array([16]))

    def is_start_of_frame_known(self):
        test_params = [(-1, False), (0, True) , (10, True)]
        for tp in test_params:
            with self.subTest(tp=tp):
                sampling_point, expected_result = tp
                self.receiver.sampling_point = sampling_point
                assert self.receiver.is_start_of_frame_known() is expected_result
