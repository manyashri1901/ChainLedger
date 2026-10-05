RANK = {"CRITICAL": 0, "WARNING": 1, "OK": 2}


def short(addr):
    if addr.startswith("0x") and len(addr) > 12:
        return f"{addr[:6]}...{addr[-4:]}"
    return addr


def build_report(findings):
    ordered = sorted(findings, key=lambda f: (RANK[f.severity], f.rule, f.subject))
    width = max((len(short(f.subject)) for f in ordered), default=0)
    lines = []
    for f in ordered:
        lines.append(
            f"[{f.severity:<8}] {f.rule:<6}  {short(f.subject):<{width}}  {f.message}"
        )
    return "\n".join(lines)