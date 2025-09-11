# Python Command Quoting Guidelines

## Shell Command Quoting Rules

### Python -c Command Quoting

**CRITICAL RULE**: Always use single quotes for `python -c` commands in shell
execution.

### Correct Quoting Pattern

#### ✅ CORRECT - Single quotes for outer command

```bash
pixi run python -c 'print("Hello World")'
pixi run python -c 'import sys; print(sys.version)'
pixi run python -c 'from module import func; func("test")'
```

#### ❌ WRONG - Double quotes for outer command

```bash
pixi run python -c "print('Hello World')"     # AVOID THIS
pixi run python -c "import sys; print(sys.version)"  # AVOID THIS
```

### Nested Quoting Rules

When you need quotes inside the Python code:

#### ✅ CORRECT - Double quotes inside single quotes

```bash
pixi run python -c 'print("This is correct")'
pixi run python -c 'logger.info("Message with quotes")'
pixi run python -c 'raise ValueError("Error message")'
```

#### ✅ CORRECT - Escaped single quotes when necessary

```bash
pixi run python -c 'print("Don'\''t do this often")'  # When you must use single quotes inside
```

#### ❌ WRONG - Conflicting quote types

```bash
pixi run python -c "print("This breaks")"     # Syntax error
pixi run python -c 'print('This breaks')'     # Syntax error
```

### Complex Examples

#### Multi-line Python code

```bash
# ✅ CORRECT
pixi run python -c '
import logging
from mymodule import MyClass

logger = logging.getLogger("test")
obj = MyClass("parameter")
result = obj.process()
print(f"Result: {result}")
'
```

#### Exception handling

```bash
# ✅ CORRECT
pixi run python -c '
try:
    from mymodule import dangerous_function
    result = dangerous_function("test")
    print("Success:", result)
except Exception as e:
    print("Error:", str(e))
'
```

#### JSON and string formatting

```bash
# ✅ CORRECT
pixi run python -c '
import json
data = {"key": "value", "number": 42}
print(json.dumps(data, indent=2))
'
```

### Why This Matters

1. **Shell parsing**: Single quotes prevent shell interpretation of special
   characters
2. **Python string literals**: Double quotes inside work naturally
3. **Consistency**: Reduces confusion and errors
4. **Portability**: Works across different shells (bash, zsh, etc.)
5. **Readability**: Clear distinction between shell and Python syntax

### Common Mistakes to Avoid

#### ❌ Double quote confusion

```bash
# This breaks because of nested double quotes
pixi run python -c "print("Hello")"
```

#### ❌ Escaping hell

```bash
# This is hard to read and error-prone
pixi run python -c "print(\"Hello \"World\"\")"
```

#### ❌ Mixed quoting without planning

```bash
# Inconsistent and confusing
pixi run python -c "import os; print('Path:', os.getcwd())"
```

### Best Practices

1. **Always start with single quotes** for `python -c`
2. **Use double quotes inside** for Python string literals
3. **Keep it simple**: Break complex commands into scripts if needed
4. **Test commands**: Verify syntax before using in automation
5. **Be consistent**: Use the same pattern throughout the project

### When to Use Scripts Instead

If your `python -c` command becomes complex, create a proper script:

```bash
# Instead of this complex command:
pixi run python -c 'very long and complex python code here...'

# Create a script:
echo 'complex python code' > scripts/temp/my_script.py
pixi run python scripts/temp/my_script.py
```

### Integration with Pixi

All pixi commands should follow this pattern:

```bash
# ✅ CORRECT pixi usage
pixi run python -c 'from mypackage import test; test()'
pixi shell -c 'python -c "print(\"In pixi shell\")"'  # Note: different context
```

Remember: **Single quotes for `python -c`, double quotes for Python strings
inside.**
