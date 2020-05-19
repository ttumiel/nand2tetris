// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed.
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

// Optimise: Could unroll the loop so that more of the screen is colored at each step
//           Could update screen only if the keyboard changes.

// Setup
(SETUP)
    @SCREEN
    D=A
    @addr
    M=D // Init screen address into addr

    @8192
    D=A
    @SCREEN
    D=D+A
    @i
    M=D // Set i=8192+SCREEN

    @END
    0;JMP

(DARK)
    @pixels
    M=-1 // pixels=0xFFFF (dark)
    @LOOP
    0;JMP

(LIGHT)
    @pixels
    M=0 // pixels=0 (light)

// Main
(LOOP)
    @i
    D=M
    @addr
    D=D-M
    @SETUP
    D;JEQ // if i==SCREEN: break

    @i
    M=M-1 // else: i--

    @pixels
    D=M // D=pixels
    @i
    A=M
    M=D // SCREEN[i] = pixels

    @LOOP
    0;JMP

(END)
    // Check for any kbd input
    @KBD
    D=M
    @DARK
    D;JGT // if KBD>0: goto DARK
    @LIGHT
    D;JEQ // if KBD==0: goto LIGHT
