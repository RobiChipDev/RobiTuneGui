import unittest
from force_reader import crc16,read_request,decode_response

class Tests(unittest.TestCase):
    def test_manual_requests(self):
        self.assertEqual(read_request(1,450).hex(),'010301c20002640b')
        self.assertEqual(read_request(1,452).hex(),'010301c40002840a')
    def test_manual_positive_example(self):
        self.assertEqual(decode_response(bytes.fromhex('01030400000084fa50'),1),132)
    def test_negative_and_word_order(self):
        b=bytes.fromhex('010304fffffec9')
        self.assertEqual(decode_response(b+crc16(b),1),-311)
        b=bytes.fromhex('010304fec9ffff')
        self.assertEqual(decode_response(b+crc16(b),1,'LL-HH'),-311)
    def test_bad_crc_station_exception_and_register(self):
        with self.assertRaises(ValueError):decode_response(bytes.fromhex('01030400000084fa51'),1)
        with self.assertRaises(ValueError):decode_response(bytes.fromhex('01030400000084fa50'),2)
        b=bytes.fromhex('018302')
        with self.assertRaisesRegex(ValueError,'exception'):decode_response(b+crc16(b),1)
        with self.assertRaises(ValueError):read_request(1,93)
        with self.assertRaises(ValueError):read_request(0,450)

if __name__=='__main__':unittest.main()
