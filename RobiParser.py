import ply.lex as lex
import ply.yacc as yacc
from enum import Enum

class EParseState( Enum ):
	End = 0
	Wait = 1
	StepLim = 2
	pass

class EParseCmd( Enum ):
	Undefined = 0
	Lin = 1
	Wait = 2

class CalcParser:
	"""
	基於 PLY 封裝的四則運算與變數解析器 Class
	"""
	# -------------------------------------
	# Lexer 規則定義 (詞法分析)
	# -------------------------------------
	tokens = ( \
		'NAME', 'NUMBER', \
		'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'EQUALS', \
		'LBRACE', 'RBRACE', 'LPAREN', 'RPAREN', 'COMMA', \
		'LT', 'GT', 'EQ', 'NE', 'LE', 'GE', \
		'LIN', 'WAIT', 'WAIT_MOTION', 'FOR', \
	)

	# 運算子與符號的正規表達式
	t_PLUS    = r'\+'
	t_MINUS   = r'-'
	t_TIMES   = r'\*'
	t_DIVIDE  = r'/'
	t_EQUALS  = r'='
	t_LT      = r'<'
	t_GT      = r'>'
	t_EQ      = r'=='
	t_NE      = r'!='
	t_LE      = r'<='
	t_GE      = r'>='
	t_LBRACE  = r'\{'
	t_RBRACE  = r'\}'
	t_LPAREN  = r'\('
	t_RPAREN  = r'\)'
	t_COMMA   = r','

	# 忽略空格、Tab 與換行。
	# (我們不強制以 \n 作為嚴格的 Token，而是讓語法結構自然分離指令，
	# 這樣使用者不管怎麼換行、排版，Parser 都能擁有極高的容錯性)
	t_ignore  = ' \t\r'

	# 關鍵字對應
	reserved = { \
		'LIN': 'LIN', \
		'WAIT': 'WAIT', \
		'WAIT_MOTION': 'WAIT_MOTION', \
		'FOR': 'FOR' \
		}

	# 處理換行符號以追蹤行號
	def t_newline( self, t: lex.LexToken ) -> None:
		r'\n+'
		t.lexer.lineno += len( t.value )
		pass

	def t_NAME( self, t: lex.LexToken ) -> lex.LexToken:
		r'[a-zA-Z_][a-zA-Z0-9_]*'
		# 檢查是否為保留字
		t.type = self.reserved.get( t.value, 'NAME' )
		return t

	def t_NUMBER( self, t: lex.LexToken ) -> lex.LexToken:
		r'\d+(\.\d+)?'
		# 自動判斷要轉換為 float 還是 int
		t.value = float( t.value ) if '.' in t.value else int( t.value )
		return t

	def t_error( self, t: lex.LexToken ) -> None:
		print( f"Lexer 錯誤: 遇到不合法的字元 '{ t.value[ 0 ] }'" )
		t.lexer.skip( 1 )

	# -------------------------------------
	# Parser 規則定義 (產生 AST 抽象語法樹)
	# -------------------------------------
	# 運算子優先級
	precedence = ( \
		( 'left', 'LT', 'GT', 'EQ', 'NE', 'LE', 'GE' ), \
		( 'left', 'PLUS', 'MINUS' ), \
		( 'left', 'TIMES', 'DIVIDE' ), \
		( 'right', 'UMINUS' ),  \
		)

	def __init__( self, stepLimit: int = 1000 ):
		self.names = {} # 變數儲存區
		self.queue = [] # 指令佇列區
		self.currLineNo = 0     # 紀錄目前解譯到的行號
		self._exec = None     # 存放當前執行狀態的產生器 (Generator)

		# 步數限制相關變數
		self.stepLimit = stepLimit	# 每次呼叫 resume 最多可執行的節點數
		self.stepCount = 0			# 目前已執行的節點計數
		
		# 建立 Lexer 與 Parser
		# 使用 module=self 讓 PLY 去綁定這個 Class 裡的 t_ 與 p_ 方法
		self.lexer = lex.lex( module = self )
		self.parser = yacc.yacc( module = self )
		pass

	# 執行與控制介面
	def getCurrLinNo( self ) -> int: 
		return self.currLineNo

	def parse_and_start( self, data ):
		"""傳入多行字串，產生 AST 並開始解譯"""
		if not data: 
			return None
		self.lexer.lineno = 1  # 重置行號
		ast = self.parser.parse( data, lexer = self.lexer )
		if not ast: 
			return None
	
		# 初始化產生器並開始第一步執行
		self._exec = self.execute( ast )
		return self.resume()

	def resume( self ) -> EParseState:
		if not self._exec:
			return EParseState.End

		# 每次呼叫 resume 時，重置計步器
		self.stepCount = 0
		
		try:
			# 推進產生器
			res = next( self._exec )
			match res:
				case EParseState.Wait:
					return EParseState.Wait

				case EParseState.StepLim:
					return EParseState.StepLim
				
		except StopIteration:
			# 解譯自然結束
			self._exec = None
			return EParseState.End

	def discard( self, keepState: bool = True ) -> None:
		"""
		丟棄尚未解譯的文本。
		keepState = True: 保留所有變數與佇列
		keepState = False: 清空所有變數與佇列
        """
		self._exec = None  # 將產生器設為 None，讓 Python 垃圾回收掉後續任務
		if keepState == False:
			self.names.clear()
			self.queue.clear()
		pass

	def execute( self, node ):
		if node is None:
			return None

		# step limit control
		self.stepCount += 1
		if self.stepCount >= self.stepLimit:
            # 暫停並交出控制權，等待下次呼叫 resume()
			yield EParseState.StepLim
			self.stepCount = 0 # 恢復執行後，重新計數

		# 若是指令列表，則依序執行
		if isinstance( node, list ):
			res = None
			for n in node: 
				res = yield from self.execute( n )
				pass
			return res

		# 已經塌縮為單一數值
		if type( node ) != tuple:
			return node

		op = node[ 0 ]
		match op:
			case 'PROGRAM':
				return ( yield from self.execute( node[ 1 ] ) )

			# ==================================
       		# Statement 處理區 (包含行號更新)
        	# ==================================
			case 'WAIT_MOTION':
				self.currLineNo = node[ 1 ]
				yield EParseState.Wait
				return None

			case 'ASSIGN':
				self.currLineNo = node[ 3 ]
				val = yield from self.execute( node[ 2 ] )
				self.names[ node[ 1 ] ] = val
				return val

			case 'LIN':
				self.currLineNo = node[ 3 ]
				arg1 = yield from self.execute( node[ 1 ] )
				arg2 = yield from self.execute( node[ 2 ] )
				cmd = [ EParseCmd.Lin, arg1, arg2 ]
				self.queue.append( cmd )
				return cmd

			case 'WAIT':
				self.currLineNo = node[ 2 ]
				arg = yield from self.execute( node[ 1 ] )
				cmd = [ EParseCmd.Wait, arg ]
				self.queue.append( cmd )
				return cmd

			case 'EXPR':
				self.currLineNo = node[ 2 ]
				return ( yield from self.execute( node[ 1 ] ) )

			case 'FOR':
				self.currLineNo = node[ 5 ]
				yield from self.execute( node[ 1 ] ) # a: 起始式
				while ( yield from self.execute( node[ 2 ] ) ): # b: 條件判斷式 (非 0 即為 True)
					yield from self.execute( node[ 4 ] ) # d: 遞迴內容 (大括號區塊)
					yield from self.execute( node[ 3 ] ) # c: 遞增/遞減式
				return None

			# ==================================
        	# Expression 處理區 (計算值)
        	# ==================================
			case 'NUMBER':
				return node[ 1 ]
			
			case 'VAR':
				if node[ 1 ] not in self.names:
					print( f"警告: 未定義的變數 '{ node[ 1 ] }'，預設回傳 0" )
					return 0
				return self.names[ node[ 1 ] ]

			case 'UMINUS':
				return -( yield from self.execute( node[ 1 ] ) )

			case 'BINOP':
				left = yield from self.execute( node[ 2 ] )
				right = yield from self.execute( node[ 3 ] )
				b_op = node[ 1 ]
				match b_op:
					case '+':
						return left + right
					case '-':
						return left - right
					case '*':
						return left * right
					case '/':
						return ( left / right ) if ( right != 0 ) else 0
					case '<':
						return 1 if ( left < right ) else 0
					case '>':
						return 1 if ( left > right ) else 0
					case '<=':
						return 1 if ( left <= right ) else 0
					case '>=':
						return 1 if ( left >= right ) else 0
					case '==':
						return 1 if ( left == right ) else 0
					case '!=':
						return 1 if ( left != right ) else 0
				pass
		pass

	# 語法：多行指令組合 (程式進入點)
	def p_program( self, p: yacc.YaccProduction ) -> None:
		'''program : statements'''
		p[ 0 ] = ( 'PROGRAM', p[ 1 ] )
		pass

	# 語法：指令列表
	def p_statements( self, p: yacc.YaccProduction ) -> None:
		'''statements : statements statement
					  | statement'''
		if len( p ) == 3:
			p[ 0 ] = p[ 1 ] + [ p[ 2 ] ]
		else:
			p[ 0 ] = [ p[ 1 ] ]
		pass

	# 語法：單行指令類別
	def p_statement_assign( self, p: yacc.YaccProduction ) -> None:
		'''statement : NAME EQUALS expression'''
		p[ 0 ] = ( 'ASSIGN', p[ 1 ], p[ 3 ], p.lineno( 1 ) )
		pass

	def p_statement_lin( self, p: yacc.YaccProduction ) -> None:
		'''statement : LIN LPAREN expression COMMA expression RPAREN'''
		p[ 0 ] = ( 'LIN', p[ 3 ], p[ 5 ], p.lineno( 1 ) )
		pass

	def p_statement_wait( self, p: yacc.YaccProduction ) -> None:
		'''statement : WAIT LPAREN expression RPAREN'''
		p[ 0 ] = ( 'WAIT', p[ 3 ], p.lineno( 1 ) )
		pass

	def p_statement_wait_motion( self, p:yacc.YaccProduction ) -> None:
		'''statement : WAIT_MOTION LPAREN RPAREN'''
		p[ 0 ] = ( 'WAIT_MOTION', p.lineno( 1 ) )
		pass

	def p_statement_expr( self, p: yacc.YaccProduction ) -> None:
		'''statement : expression'''
		p[ 0 ] = ( 'EXPR', p[ 1 ], p.lineno( 1 ) )
		pass

	def p_statement_for( self, p: yacc.YaccProduction ) -> None:
		'''statement : FOR LPAREN statement COMMA expression COMMA statement RPAREN LBRACE statements RBRACE'''
		p[ 0 ] = ( 'FOR', p[ 3 ], p[ 5 ], p[ 7 ], p[ 10 ], p.lineno( 1 ) )
		pass

	# 語法：表達式
	def p_expression_binop( self, p: yacc.YaccProduction ) -> None:
		'''expression : expression PLUS expression
					  | expression MINUS expression
					  | expression TIMES expression
					  | expression DIVIDE expression
					  | expression LT expression
					  | expression GT expression
					  | expression EQ expression
					  | expression NE expression
					  | expression LE expression
					  | expression GE expression'''
		p[ 0 ] = ( 'BINOP', p[ 2 ], p[ 1 ], p[ 3 ] )
		pass

	def p_expression_uminus( self, p: yacc.YaccProduction ) -> None:
		'''expression : MINUS expression %prec UMINUS'''
		p[ 0 ] = ( 'UMINUS', p[ 2 ] )
		pass

	def p_expression_group( self, p: yacc.YaccProduction ) -> None:
		'''expression : LPAREN expression RPAREN'''
		p[ 0 ] = p[ 2 ]
		pass

	def p_expression_number( self, p: yacc.YaccProduction ) -> None:
		'''expression : NUMBER'''
		p[ 0 ] = ( 'NUMBER', p[ 1 ] )
		pass

	def p_expression_name( self, p: yacc.YaccProduction ) -> None:
		'''expression : NAME'''
		p[ 0 ] = ( 'VAR', p[ 1 ] )
		pass

	def p_error( self, p: yacc.YaccProduction ) -> None:
		if p:
			print( f"Parser 錯誤: 語法錯誤發生於 '{ p.value }'" )
		else:
			print( "Parser 錯誤: 語句提早結束或不完整" )
		pass

# ==========================================
# 測試與使用範例
# ==========================================
if __name__ == '__main__':
	calc = CalcParser()
    
	script = """
	X = 1
	WAIT_MOTION()
	LIN(X, 100)
    
	FOR(I=0, I<2, I=I+1) {
		LIN(I, I*2)
		WAIT_MOTION()
	}
    
	Y = 999
	"""
    
	print("--- 第一階段：開始解析並執行 ---")
	status = calc.parse_and_start( script )
    
	# 模擬 Caller 的事件迴圈 (Event Loop)
	while status == EParseState.Wait:
		print( f"\n[系統狀態] Parser 暫停中... 目前行號: { calc.getCurrLinNo() }" )
		print( f"目前變數: { calc.names }" )
		print( f"目前佇列: { calc.queue }" )
        
		# 示範在第二次遇到 WAIT_MOTION 時選擇丟棄 (Discard)
		if calc.names.get( 'I' ) == 1:
			print( ">>> Caller 決定中斷解譯 (Discard)，並保留變數狀態！" )
			status = calc.discard( keepState = True )
			break
            
		print(">>> Caller 決定繼續執行 (Resume)...")
		status = calc.resume()
        
	print( f"\n--- 最終解譯器狀態: { status } ---" )
	print( f"最終變數 (names): { calc.names }" )
	print( f"最終佇列 (queue): { calc.queue }" )