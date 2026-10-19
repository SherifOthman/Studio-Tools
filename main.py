"""
main.py  –  Studio Tools entry point.
Run:  python main.py
"""

import sys
import os

# Allow  `python main.py`  from the project root regardless of cwd.
sys.path.insert(0, os.path.dirname(__file__))

from app.shell import Shell


def main():
    app = Shell()
    app.mainloop()


if __name__ == "__main__":
    main()
