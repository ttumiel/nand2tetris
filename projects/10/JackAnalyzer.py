from pathlib import Path
import argparse

from CompilationEngine import CompilationEngine

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Jack Analyzer.')
    parser.add_argument('path', type=str,
                        help='Filename or directory to process.')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print compilation progress.')
    args = parser.parse_args()

    path = Path(args.path)
    if path.is_dir():
        for f in path.iterdir():
            if f.suffix == '.jack':
                if args.verbose: print('Compiling', f)
                c = CompilationEngine(f, str(f)[:-4]+'xml')
                c.compile()
    else:
        if args.verbose: print('Compiling', path)
        c = CompilationEngine(path, str(path)[:-4]+'xml')
        c.compile()
