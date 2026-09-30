"""Check paired structure, commands and numeric defaults; meaning needs review."""
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
a=(root/'README.md').read_text(encoding='utf-8')
b=(root/'README.ko.md').read_text(encoding='utf-8')
for label,pattern in [('sections',r'<!-- section: (.*?) -->'),('commands',r'```[^\n]*\n(.*?)```'),('inline technical tokens',r'`([^`\n]+)`')]:
    if re.findall(pattern,a,re.S)!=re.findall(pattern,b,re.S):
        raise SystemExit(f'README mismatch: {label}')
print('README structure, command blocks and inline tokens match; semantic review is still required.')
