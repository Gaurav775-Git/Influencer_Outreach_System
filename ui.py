from colorama import Fore, Style, init
from tabulate import tabulate

init(autoreset=True)

def banner(text):
    print(f"\n{Fore.CYAN}{'═' * 60}\n  {text}\n{'═' * 60}{Style.RESET_ALL}")

def info(msg): print(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} {msg}")
def ok(msg):   print(f"{Fore.GREEN}[ OK ]{Style.RESET_ALL} {msg}")
def warn(msg): print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {msg}")
def err(msg):  print(f"{Fore.RED}[FAIL]{Style.RESET_ALL} {msg}")

def table(rows, headers):
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))

def progress(current, total, label=""):
    pct = int(current / total * 100) if total else 0
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    print(f"\r{Fore.YELLOW}[{bar}] {pct:3d}%  {label}{Style.RESET_ALL}",
          end="", flush=True)
    if current == total:
        print()