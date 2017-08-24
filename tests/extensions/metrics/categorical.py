import unittest
import torch
from inferno.extensions.metrics import IOU


class TestCategorical(unittest.TestCase):
    def test_iou(self):
        predicted_image = torch.zeros(*(2, 10, 10))
        predicted_image[:, 0:4, 0:4] = 1
        target_image = torch.zeros(*(2, 10, 10))
        target_image[:, 0:3, 0:3] = 1
        expected_iou = (3 * 3)/(4 * 4)
        iou = IOU()(predicted_image[None, ...], target_image[None, ...])
        self.assertAlmostEqual(iou, expected_iou, places=4)

if __name__ == '__main__':
    unittest.main()