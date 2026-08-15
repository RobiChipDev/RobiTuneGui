import sys
import time
from McpItf import CMcpItf
from RobiGui import CRobiGui

def main() -> int:
	# create interactive application
	gui = CRobiGui()
	gui.exec()
	return 0

if __name__ == '__main__':
	sys.exit( main() )
	pass