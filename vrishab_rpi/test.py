import asyncio
import math
import time

from moteus_interface import GearReductionDeg

def main():
	a = GearReductionDeg(1)
	deg = a.deg_mpos(360.0)
	mpos = a.mpos_deg(1)
	print(f"deg = {deg}, mpos = {mpos}")

if __name__ == '__main__':
	main()
