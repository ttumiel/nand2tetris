// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// Optimise: If R2>R1, switch them

// Setup
@R2
M=0 // Set R2=0

// Main
(LOOP)
    @R1
    D=M // D=R1
    @END
    D;JEQ // if i==0: exit

    @1
    D=D-A // i--
    @R1
    M=D // R1=i

    @R0
    D=M // D=R0
    @R2
    M=D+M // R2=R2+R1

    @LOOP
    0;JMP

// Infinite loop to terminate program
(END)
    @END
    0;JMP
