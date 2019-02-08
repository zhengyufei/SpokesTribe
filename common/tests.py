from django.test import TestCase

from .function import phonecheck, isidcard

# Create your tests here.
class test_phonecheck(TestCase):
    def test1(self):
        self.assertEqual(phonecheck('13408544339')[0], True)

    def test2(self):
        self.assertEqual(phonecheck('134085443391')[0], False)

    def test3(self):
        self.assertEqual(phonecheck('1340854433')[0], False)

    def test4(self):
        self.assertEqual(phonecheck('1340854433A')[0], False)

class test_isidcard(TestCase):
    def test1(self):
        self.assertEqual(isidcard('152104198710210013')[0], True)

    def test2(self):
        self.assertEqual(isidcard('152104198710210014')[0], False)
