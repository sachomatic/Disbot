from os import path
from pickle import Pickler
from sys import argv, orig_argv
from tkinter import messagebox
from traceback import print_exc
from urllib.parse import parse_qsl


if __name__ != "__main__":
    raise ImportError("This script should not be imported")

consm = argv == orig_argv

try:
    if len(argv) > 0:
        p = argv[1]
    else:
        p = input("Path to the module : ")
    if not path.exists(p):
        if consm is False:
            messagebox.showerror("File not found", p)
        raise FileNotFoundError(p)
    inp = open(p)

    if len(argv) > 1:
        p = argv[1]
    else:
        p = input("Path to the result : ")
    if path.exists(p):
        match input("Warning ! This operation will overwrite the result file, continue ? ").lower():
            case "y" | "yes":
                pass
            case _:
                raise RuntimeError("Cancelled.")
    out = open(p, "wb")

    if len(argv) > 2:
        p = argv[2]
    else
        p = input("Pickle protocol to use between 0 and 5 : ")
    if p.isdigit():
        p = int(p)
        if p in range(6):
        p = int(p)
    
    
    Pickler(out)

except BaseException:
    try:
        inp.close()
    except NameError:
        pass
    try:
        out.close()
    except NameError:
        pass
    print_exc()
