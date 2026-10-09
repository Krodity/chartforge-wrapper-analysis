import sys


def scan(src):
    lines = src.split("\n")
    code = [False] * len(lines)
    com = [False] * len(lines)
    i, n, ln = 0, len(src), 0
    state = None
    tmpl_depth = []
    prev = ""
    spans = []
    cstart = 0
    while i < n:
        c = src[i]
        nx = src[i + 1] if i + 1 < n else ""
        if c == "\n":
            ln += 1
            if state == "line":
                spans.append((cstart, i))
                state = None
            i += 1
            continue
        if state == "line":
            com[ln] = True
        elif state == "block":
            if not c.isspace():
                com[ln] = True
            if c == "*" and nx == "/":
                spans.append((cstart, i + 2))
                state = None
                i += 2
                continue
        elif state in ("'", '"'):
            code[ln] = True
            if c == "\\":
                i += 2
                continue
            if c == state:
                state = None
        elif state == "`":
            code[ln] = True
            if c == "\\":
                i += 2
                continue
            if c == "`":
                state = tmpl_depth.pop() if tmpl_depth and tmpl_depth[-1] != "`" else None
                if state == "`":
                    state = None
            elif c == "$" and nx == "{":
                tmpl_depth.append("`")
                state = None
                i += 2
                continue
        else:
            if c == "/" and nx == "/":
                cstart = i
                state = "line"
                com[ln] = True
                i += 2
                continue
            if c == "/" and nx == "*":
                cstart = i
                state = "block"
                com[ln] = True
                i += 2
                continue
            if c == "/" and (prev == "" or prev in "(,=:[!&|?{};+-*%<>~^" or src[max(0,i-6):i].rstrip().endswith("return")):
                code[ln] = True
                j, cls = i + 1, False
                while j < n and src[j] != "\n":
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == "[":
                        cls = True
                    elif src[j] == "]":
                        cls = False
                    elif src[j] == "/" and not cls:
                        break
                    j += 1
                i = j + 1
                prev = "/"
                continue
            if c in "'\"`":
                state = c
                code[ln] = True
            elif c == "}" and tmpl_depth and tmpl_depth[-1] == "`":
                tmpl_depth.pop()
                state = "`"
                code[ln] = True
            elif c == "{" and tmpl_depth:
                tmpl_depth.append("{")
                code[ln] = True
            elif c == "}" and tmpl_depth and tmpl_depth[-1] == "{":
                tmpl_depth.pop()
                code[ln] = True
            elif not c.isspace():
                code[ln] = True
            if not c.isspace():
                prev = c if c not in "'\"`" else "a"
        i += 1
    if state == "line":
        spans.append((cstart, n))
    total = len(lines) - (1 if lines and lines[-1] == "" else 0)
    blank = sum(1 for k in range(total) if not code[k] and not com[k])
    only_com = sum(1 for k in range(total) if com[k] and not code[k])
    mixed = sum(1 for k in range(total) if com[k] and code[k])
    code_n = sum(1 for k in range(total) if code[k])
    return (total, code_n, only_com, mixed, blank), spans, code


def comment_lines(src, spans, code):
    out = []
    for a, b in spans:
        ln = src.count("\n", 0, a)
        for k, part in enumerate(src[a:b].split("\n")):
            text = part.rstrip()
            if text.strip():
                out.append((ln + k + 1, "trailing" if code[ln + k] else "comment", text))
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    dump = args[:1] == ["--dump"]
    if dump:
        args = args[1:]
    else:
        print("file\ttotal\tcode\tcomment_only\ttrailing\tblank")
    for p in args:
        with open(p, encoding="utf-8", errors="replace") as f:
            src = f.read()
        r, spans, code = scan(src)
        if dump:
            for ln, kind, text in comment_lines(src, spans, code):
                print(p, ln, kind, text, sep="\t")
        else:
            print(p, *r, sep="\t")
