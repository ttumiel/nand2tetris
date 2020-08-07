"""The symbol table stores the locations of each of the symbolic
variable names and the relative scope of those variables.

The tables contains the name of the variable, the type (int, ClassName)
and the kind (field, local)
"""

class SymbolTable:
    def __init__(self, global_table=None):
        self.global_table = global_table
        self.table = {}
        self.counts = {'local': 0, 'argument': 0, 'static': 0, 'field': 0}

    def define(self, name, type, kind):
        index = self.counts[kind]
        assert name not in self.table
        self.table[name] = (type, kind, index)
        self.counts[kind] = index + 1

    def var_count(self, kind):
        return self.counts[kind]

    def __getitem__(self, name):
        if name in self.table:
            return self.table[name]
        elif self.global_table is not None:
            return self.global_table[name]

    def __contains__(self, name):
        g = name in self.global_table if self.global_table is not None else False
        return name in self.table or g

    def type_of(self, name):
        return self[name][0]

    def kind_of(self, name):
        return self[name][1]

    def count_of(self, name):
        return self[name][2]

    def new_scope(self):
        return SymbolTable(self)

    def __repr__(self):
        return repr(self.table)
