from compiler import to_program
from reader import read, Literal, Expr
from rpython.config.translationoption import get_combined_translation_config
import base
import space
import sys, os
config = get_combined_translation_config(translating=True)
#config.translation.continuation = True


def interactive():
    module = space.Module('shell', {}, extends=base.module)


    prompt = "pyl> "
    os.write(1, prompt)
    source = os.read(0, 4096)
    while source != "":
        try:
            program = to_program(read(source))
            os.write(1, program.call([module]).repr())
            os.write(1, "\n")
        except space.Error as error:
            os.write(1, error.__class__.__name__ + ": " + error.message + "\n")
        os.write(1, prompt)
        source = os.read(0, 4096)
    if source == "":
        os.write(1, "\n")

def entry_point(argv):
    if len(argv) <= 1:
        interactive()
    else:
        os.write(1, "?")
    return 0

def target(*args):
    return entry_point, None

if __name__=='__main__':
    sys.exit(entry_point(sys.argv))
