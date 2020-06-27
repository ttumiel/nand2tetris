from pathlib import Path
from CompilationEngine import CompilationEngine

def wrap_test_path(path):
    def _inner():
        for f in Path(path).iterdir():
            if f.suffix == '.jack':
                print(f, end=" ")
                c = CompilationEngine(f, 'tmp.xml')
                c.compile()

                with open(str(f)[:-4] + 'xml') as cmp, open('tmp.xml') as tst:
                    assert cmp.read() == tst.read()
                print("Passed")
    return _inner

test_square = wrap_test_path('Square')
test_expression_less_square = wrap_test_path('ExpressionLessSquare')
test_array = wrap_test_path('ArrayTest')

if __name__ == '__main__':
    test_square()
    test_expression_less_square()
    test_array()
