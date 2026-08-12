import sys
import time
from McpItf import CMcpItf

def main() -> int:
	print( "RobiTune Test Interface" )

	mcp = CMcpItf( 0 )
	time.sleep( 1.0 )

	mcp.Cmd_GetMcpVer()
	return 0

if __name__ == '__main__':
	sys.exit( main() )