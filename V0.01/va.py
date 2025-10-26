import os, json, shlex, sys, datetime as dt, textwrap
from pathlib import Path

STATE_PATH = Path.home() / ".va_state.json"

# ---------- Persistence ----------
def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"notes": [], "todos": [], "created": dt.datetime.now().isoformat()}

def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2))

STATE = load_state()

# ---------- Command registry ----------
COMMANDS = {}
ALIASES = {}

def command(name, *, aliases=(), help=""):
    def wrap(func):
        COMMANDS[name] = {"fn": func, "help": help.strip()}
        for a in aliases:
            ALIASES[a] = name
        return func
    return wrap

def resolve(cmd):
    if cmd in COMMANDS:
        return cmd
    if cmd in ALIASES:
        return ALIASES[cmd]
    return None

# ---------- Utilities ----------
def now():
    return dt.datetime.now()

def echo_box(s: str):
    w = 72
    lines = textwrap.wrap(s, width=w) if "\n" not in s else s.splitlines()
    print("┌" + "─"*w + "┐")
    for line in lines:
        print("│" + line.ljust(w) + "│")
    print("└" + "─"*w + "┘")

HISTORY = []

# ---------- Built-in commands ----------
@command("help", aliases=("?",), help="""
help [command] — show help (for all commands or a specific one)
""")
def _help(args):
    if args:
        cmd = resolve(args[0])
        if not cmd:
            print(f"No such command: {args[0]}")
            return
        h = COMMANDS[cmd]["help"] or "(no help text)"
        echo_box(f"{cmd}\n\n{h}")
        return
    # overview
    echo_box("Commands:")
    names = sorted(COMMANDS)
    width = max(len(n) for n in names)
    for n in names:
        h = COMMANDS[n]["help"].splitlines()[0] if COMMANDS[n]["help"] else ""
        print(f"  {n.ljust(width)}  {h}")

@command("time", aliases=("date",), help="time — show current date/time")
def _time(args):
    print(now().strftime("%Y-%m-%d %H:%M:%S"))

@command("say", help="say <text> — repeat back your text")
def _say(args):
    if not args:
        print("Usage: say <text>")
        return
    print(" ".join(args))

@command("note", aliases=("addnote","n"), help="""
note <text> — save a quick note
note list     — list notes
""")
def _note(args):
    if not args:
        print("Usage: note <text> | note list")
        return
    if args[0] == "list":
        if not STATE["notes"]:
            print("(no notes)")
        else:
            for i, n in enumerate(STATE["notes"], 1):
                print(f"{i}. {n['when']} — {n['text']}")
        return
    text = " ".join(args)
    STATE["notes"].append({"when": now().isoformat(timespec="seconds"), "text": text})
    save_state(STATE)
    print("Saved note.")

@command("todo", aliases=("t","task"), help="""
todo add <text>     — add a todo
todo list           — list todos
todo done <number>  — mark done (by number)
""")
def _todo(args):
    if not args or args[0] not in ("add","list","done"):
        print("Usage:\n  todo add <text>\n  todo list\n  todo done <number>")
        return
    sub = args[0]
    if sub == "add":
        text = " ".join(args[1:]).strip()
        if not text:
            print("Provide a task description.")
            return
        STATE["todos"].append({"text": text, "done": False, "created": now().isoformat(timespec="seconds")})
        save_state(STATE)
        print("Added.")
    elif sub == "list":
        if not STATE["todos"]:
            print("(no todos)")
            return
        for i, t in enumerate(STATE["todos"], 1):
            box = "[x]" if t["done"] else "[ ]"
            print(f"{i:2}. {box} {t['text']}")
    elif sub == "done":
        if len(args) < 2 or not args[1].isdigit():
            print("Provide the todo number to mark done.")
            return
        idx = int(args[1]) - 1
        if idx < 0 or idx >= len(STATE["todos"]):
            print("Invalid number.")
            return
        STATE["todos"][idx]["done"] = True
        save_state(STATE)
        print("Marked done.")

@command("history", help="history — show recent commands")
def _history(args):
    for i, line in enumerate(HISTORY[-50:], 1):
        print(f"{i:2}: {line}")

@command("clear", help="clear — clear the screen")
def _clear(args):
    os.system("cls" if os.name == "nt" else "clear")

@command("exit", aliases=("quit","q"), help="exit — leave the assistant")
def _exit(args):
    print("Bye!")
    sys.exit(0)

# ---------- Intent fallback (very simple) ----------
INTENT_MAP = [
    ({"note","remember","jot"}, "note"),
    ({"task","todo","remind"}, "todo"),
    ({"time","date","clock"}, "time"),
    ({"repeat","say","echo"}, "say"),
    ({"help"}, "help"),
]

def guess_intent(tokens):
    words = set(w.lower() for w in tokens)
    best = None
    for keys, cmd in INTENT_MAP:
        if keys & words:
            best = cmd
            break
    return best

# ---------- Main loop ----------
BANNER = """\
Command-line Virtual Assistant
Type 'help' to see commands. Ctrl+C or 'exit' to quit.
"""

def main():
    print(BANNER)
    while True:
        try:
            line = input("va> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            _exit([])
        if not line:
            continue
        HISTORY.append(line)
        try:
            parts = shlex.split(line)
        except ValueError as e:
            print(f"Parse error: {e}")
            continue
        cmd_token, *args = parts
        cmd = resolve(cmd_token)
        if not cmd:
            # try intent guess
            guess = guess_intent(parts)
            if guess:
                cmd = guess
                # pass whole line minus guessed word as args (simple heuristic)
                args = [a for a in args if a.lower() not in ("please","me","a","the")]
                # Special case: if guessed note and no args, take rest of line
                if cmd == "note" and not args:
                    args = [" ".join(parts)]
            else:
                print(f"Unknown command: {cmd_token}. Try 'help'.")
                continue
        try:
            COMMANDS[cmd]["fn"](args)
        except SystemExit:
            raise
        except Exception as e:
            print(f"Error running '{cmd}': {e}")

if __name__ == "__main__":
    main()
