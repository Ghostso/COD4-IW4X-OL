import re

SRC = r"CODOLServer\_wegame_985.txt"


def main():
    text = open(SRC, "r", encoding="utf-8", errors="replace").read()
    blocks = re.split(r"\n(?=  \S)", text)

    factory_with_985 = []
    factory_all = []
    for b in blocks:
        if "factory=True" not in b:
            continue
        head = b.strip().splitlines()[0].strip()
        has985 = "985-immediate" in b
        factory_all.append((head, has985))
        if has985:
            factory_with_985.append(b.strip())

    print("=" * 100)
    print("ALL Tenio factory DLLs found under WeGame")
    print("=" * 100)
    for head, has985 in factory_all:
        flag = "  <== has 985 immediate" if has985 else ""
        print(f"  {head}{flag}")

    print()
    print("=" * 100)
    print("Factory DLLs that DO reference immediate 985")
    print("=" * 100)
    for b in factory_with_985:
        print(b)
        print("-" * 90)


if __name__ == "__main__":
    main()
