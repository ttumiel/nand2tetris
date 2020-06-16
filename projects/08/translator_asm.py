"""
Contains the assembly code that is used to generate assembly
instructions from virtual machine code.
"""

#########################################
### Arithmetic and logical operations ###
#########################################

# Loads 2 args off the stack into M and D
# M = arg1, D = arg2
load_2_args = """@SP
M=M-1 // SP--
A=M
D=M // D=*SP
@SP
A=M-1 // SP--
"""

# Load one arg off the stack into D
load_1_arg = """@SP
A=M-1 // SP--
"""

# Apply an arithmetic operation to 2 args
arth_2_args = "M=M{op}D // *SP+D"

# Apply a logic operation to 2 args
log_2_args = """D=M-D
@LOG_{cmp}_true.{uuid}
D;J{cmp}
@SP
A=M-1
M=0
@LOG_{cmp}_false.{uuid}
0;JMP
(LOG_{cmp}_true.{uuid})
@SP
A=M-1
M=-1
(LOG_{cmp}_false.{uuid})"""

# apply an operation to 1 arg
asm_1_arg = "M={op}M // *SP=D"



#########################################
###      Memory Segment commands      ###
#########################################

# push from a segment of memory
seg_push = """@{segment}
D=M // D=base_addr
@{addr}
A=D+A // A=base_addr+offset
D=M // D=val
@SP
A=M
M=D
@SP
M=M+1"""

# pop to a segment of memory
seg_pop = """@{segment}
D=M // D=base_addr
@{addr} // offset
D=D+A // D = base_addr+offset
@R13
M=D
@SP
AM=M-1 //SP--
D=M // D=val
@R13
A=M
M=D"""

# pop to an address
address_pop = """@SP
AM=M-1
D=M
@{addr}
M=D"""

# push to and address
address_push = """@{addr}
D={val}
@SP
A=M
M=D
@SP
M=M+1"""



#########################################
###         Function Commands         ###
#########################################

# Args=SP-5-nargs (i.e. function arguments on stack)
# LCL = SP
call_asm = """@{offset}
D=A
@SP
D=M-D // D=SP-5-nargs
@ARG
M=D // ARG = SP-5-nargs
@SP
D=M
@LCL
M=D
@{name}
0;JMP
({name}$ret.{i})"""


# Create a label from a function name. By convention
# the name is filename.funcname
func_asm = "({funcname})"


# Return from a function by restoring saved caller state
# and popping the returned value.
return_asm_pre = """@LCL
D=M
@R14
M=D
@5
A=D-A
D=M
@R15
M=D
"""

return_asm_post = """
@ARG // RESTORE SP
D=M+1
@SP
M=D //SP=arg+1
@R14
D=M-1 // Restore THAT
@R14
AM=D
D=M
@THAT
M=D // THAT = *(LCL-1)
@R14 // Restore THIS
D=M-1 // LCL-2
@R14
AM=D
D=M
@THIS
M=D // THIS = *(LCL-2)
@R14 // Restore ARG
D=M-1 // LCL-3
@R14
AM=D
D=M
@ARG
M=D // ARG = *(LCL-3)
@R14 // Restore LCL
D=M-1 // LCL-4
@R14
AM=D
D=M
@LCL
M=D // LCL = *(LCL-4)
@R15
A=M
0;JMP // goto lcl-5 == retAddr"""
