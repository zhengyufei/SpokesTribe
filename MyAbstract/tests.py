from django.test import TestCase

from .funtions import services_contract

# Create your tests here.
class test_services_contract(TestCase):
    def test1(self):
        self.assertEqual(services_contract(700), (700,0))

    def test2(self):
        self.assertEqual(services_contract(800), (800,0))

    def test3(self):
        self.assertEqual(services_contract(1000), (960,40))

    def test4(self):
        self.assertEqual(services_contract(4000), (3360,640))

    def test5(self):
        self.assertEqual(services_contract(15000), (12600,2400))

    def test6(self):
        self.assertEqual(services_contract(25000), (21000,4000))

    def test7(self):
        self.assertEqual(services_contract(40000), (32400,7600))

    def test8(self):
        self.assertEqual(services_contract(62500), (49500,13000))

    def test9(self):
        self.assertEqual(services_contract(70000), (54600,15400))

    def test10(self):
        self.assertEqual(services_contract(100000), (75000,25000))

