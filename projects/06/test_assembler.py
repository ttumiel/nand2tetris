from assembler import *

def test_parse_computation_match():
    assert parse_computation('0')=='101010'
    assert parse_computation('1')=='111111'
    assert parse_computation('-1')=='111010'

    assert parse_computation('D')=='001100'
    assert parse_computation('A')=='110000'
    assert parse_computation('M')=='110000'

    assert parse_computation('!D')=='001101'
    assert parse_computation('!A')=='110001'
    assert parse_computation('!M')=='110001'

    assert parse_computation('-D')=='001111'
    assert parse_computation('-A')=='110011'
    assert parse_computation('-M')=='110011'

    assert parse_computation('D+1')=='011111'
    assert parse_computation('A+1')=='110111'
    assert parse_computation('M+1')=='110111'

    assert parse_computation('D-1')=='001110'
    assert parse_computation('A-1')=='110010'
    assert parse_computation('M-1')=='110010'

    assert parse_computation('D+A')=='000010'
    assert parse_computation('D+M')=='000010'

    assert parse_computation('D-A')=='010011'
    assert parse_computation('D-M')=='010011'

    assert parse_computation('A-D')=='000111'
    assert parse_computation('M-D')=='000111'

    assert parse_computation('D&A')=='000000'
    assert parse_computation('D&M')=='000000'

    assert parse_computation('D|A')=='010101'
    assert parse_computation('D|M')=='010101'

def test_assembler():
    for file in ['add', 'max', 'rect', 'pong']:
        name = f"{file}/{file.capitalize()}"
        assembler(f"{name}.asm")
        assert open(f"{name}.hack").read() == open(f"{file}/{file}_ans.hack").read()

if __name__=='__main__':
    test_parse_computation_match()
    test_assembler()
