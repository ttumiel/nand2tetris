"Writes commands in the Jack->Hack VM language."

class VMWriter:
    def __init__(self, filename):
        self.file = open(filename, 'w')

    def write_push(self, segment, index):
        self.write(f'push {segment} {index}')

    def write_pop(self, segment, index):
        self.write(f'pop {segment} {index}')

    def write_arithmetic(self, command):
        self.write(f'{command}')

    def write_label(self, label):
        self.write(f'({label})')

    def write_goto(self, label):
        self.write(f'goto {label}')

    def write_if(self, label):
        self.write(f'if-goto {label}')

    def write_call(self, function, nargs):
        self.write(f'call {function} {nargs}')

    def write_call(self, function, nlocals):
        self.write(f'call {function} {nlocals}')

    def write_return(self):
        self.write('return')

    def write(self, cmd):
        self.file.write(cmd+'\n')

    def close(self):
        self.file.close()

    def __del__(self):
        self.close()
