---
inclusion: always
---

# Python Command Quoting

## Essential Rule

**Always use single quotes for `python -c` commands, double quotes inside for
Python strings.**

## Correct Pattern

```bash
# ✅ Correct
pixi run python -c 'print("Hello World")'
pixi run python -c 'import sys; print(sys.version)'
pixi run python -c 'from module import func; func("test")'

# ❌ Wrong
pixi run python -c "print('Hello World')"     # Breaks with nested quotes
```

## Complex Examples

### Multi-line Code

```bash
pixi run python -c '
import json
from mymodule import MyClass

obj = MyClass("parameter")
result = obj.process()
print(f"Result: {result}")
'
```

### Exception Handling

```bash
pixi run python -c '
try:
    from mymodule import dangerous_function
    result = dangerous_function("test")
    print("Success:", result)
except Exception as e:
    print("Error:", str(e))
'
```

## Why This Matters

1. **Shell parsing** - Single quotes prevent shell interpretation
2. **Python strings** - Double quotes inside work naturally
3. **Consistency** - Reduces confusion and errors
4. **Portability** - Works across different shells

## When to Use Scripts Instead

For complex commands, create a script:

```bash
# Instead of complex python -c
echo 'complex python code' > scripts/temp/my_script.py
pixi run python scripts/temp/my_script.py
```

**Remember: Single quotes outside, double quotes inside.**
