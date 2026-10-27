import unittest
from operation import assemble
class Inventory(unittest.TestCase):
    def test_last_kit(self): self.assertEqual(assemble(2,1,0,1),(True,0,0,1))
    def test_empty_stock(self): self.assertEqual(assemble(0,0,0,1),(False,0,0,0))
    def test_invalid_quantity(self): self.assertEqual(assemble(2,1,0,0),(False,2,1,0))
