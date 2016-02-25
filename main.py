from rpython.rlib.objectmodel import we_are_translated, keepalive_until_here
from runtime.util import STDIN, STDOUT, STDERR, read_file, write
from runtime.stdlib import api
from runtime import main
import space
import sys, os

@space.Builtin
def system_init(argv):
    module_src = argv[0]
    assert isinstance(module_src, space.String)
    module = space.Module(u'main', {}, extends=base.module)
    result = module_resolution.load_module(module_src.string.encode('utf-8'), module)
    try:
        main_func = module.getattr(u"main")
    except space.Error as error:
        pass
    else:
        result = main_func.call([space.List(argv)])
    return space.null

def force_config(config):
    config.translation.continuation = True

def target(driver, args):
    driver.exe_name = "lever"
    force_config(driver.config)
    return main.new_entry_point(driver.config), None

def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__=='__main__':
    from rpython.config.translationoption import get_combined_translation_config
    config = get_combined_translation_config(translating=True)
    force_config(config)
    sys.exit(main.new_entry_point(config)(sys.argv))
