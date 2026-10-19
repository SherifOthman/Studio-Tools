# rtl.py – stub kept so imports don't break; Arabic removed.
# All functions return LTR values.

def start() -> str:  return "left"
def end()   -> str:  return "right"
def anchor_start() -> str: return "w"
def anchor_end()   -> str: return "e"
def text_anchor()  -> str: return "w"
def justify()      -> str: return "left"
def is_rtl()       -> bool: return False
def row(parent, fg_color="transparent"):
    import customtkinter as ctk
    return ctk.CTkFrame(parent, fg_color=fg_color)
