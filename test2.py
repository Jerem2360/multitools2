import __main__
import sys


print("test2.py")
main_file = open(__main__.__file__, "r+")
main_code = main_file.read()
main_file.close()

relaunch_sys = sys
relaunch_sys.modules['sys'] = relaunch_sys
res = exec(compile(main_code, __main__.__file__, "exec"), {"sys": relaunch_sys}, {})
print("exec result:", res)

