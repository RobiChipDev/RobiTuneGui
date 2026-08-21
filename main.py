import sys
import time
from McpItf import CMcpItf
from RobiGui import CRobiGui
from RobiPlanner import CRobiPlanner

def main() -> int:
	mcp = CMcpItf()
	planner = CRobiPlanner( mcp )

	# create interactive application
	gui = CRobiGui( mcp, planner )
	gui.exec()
	return 0

if __name__ == '__main__':
	sys.exit( main() )
	pass