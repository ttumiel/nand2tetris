from pathlib import Path
from translator import translator


def test_program_flow():
    for p in ['ProgramFlow/BasicLoop/BasicLoop',
              'ProgramFlow/FibonacciSeries/FibonacciSeries']:
        with open(p+'.asm', 'w') as fout:
            translator([p+'.vm'], fout, annotate=True)


def test_function_calls():
    for p in [
        './FunctionCalls/SimpleFunction',
        './FunctionCalls/NestedCall',
        './FunctionCalls/FibonacciElement',
        './FunctionCalls/StaticsTest'
    ]:
        p = Path(p)
        files = [fin for fin in p.iterdir() if fin.suffix == '.vm']
        with open(str(p/p.stem)+'.asm', 'w') as fout:
            translator(files, fout, annotate=True)

if __name__=='__main__':
    test_program_flow()
    test_function_calls()
