"""Build a trimmed, vendored CPython inventory for offline tests (SPEC T5).

Fetches the real docs.python.org inventory once (build time only), keeps a
handful of re.* rows with their authentic library/re.html#... uris, and writes
a valid v2 objects.inv. Tests then consume this vendored file with NO network.
"""
import sphobjinv as soi

SRC = "https://docs.python.org/3/objects.inv"
KEEP = {
    "re.match",        # py:function
    "re.Match",        # py:class   <-- the case clash vs re.match
    "re.compile",      # py:function
    "re.Match.group",  # py:method
    "re.Pattern",      # py:class (bonus, another cased name)
}

src = soi.Inventory(url=SRC)
out = soi.Inventory()
out.project = "Python"
out.version = "3"
kept = []
for o in src.objects:
    if o.name in KEEP:
        # Store the EXPLICIT, case-preserved anchor (uri_expanded), NOT the real
        # CPython `$` shorthand. mystmd's intersphinx loader lowercases the `$`
        # expansion, which would collapse re.Match onto re.match; explicit
        # anchors resolve case-sensitively in BOTH mystmd and Sphinx. The uri is
        # still the authentic library/re.html#... target. (See FINDINGS.md.)
        out.objects.append(soi.DataObjStr(
            name=o.name, domain=o.domain, role=o.role,
            priority=o.priority, uri=o.uri_expanded, dispname=o.dispname))
        kept.append((o.name, o.domain + ":" + o.role, o.uri_expanded))

# sanity: we must have distinct rows for re.match and re.Match
names = {o.name for o in out.objects}
assert "re.match" in names and "re.Match" in names, "missing case-clash rows"

data = out.data_file()               # plaintext v2 payload
ztext = soi.compress(data)           # zlib-compress body
soi.writebytes("fixtures/inv/python.objects.inv", ztext)

print(f"wrote fixtures/inv/python.objects.inv with {len(out.objects)} objects:")
for name, role, uri in sorted(kept):
    print(f"  {name:20s} {role:14s} {uri}")
