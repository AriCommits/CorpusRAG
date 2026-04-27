content = open('src/utils/auth.py').read()

# 1. Add __future__ import at the very top
content = 'from __future__ import annotations\n\n' + content

# 2. Remove the misplaced lazy imports that ended up before the docstring
old = (
    '    async def authenticate_request(\n'
    '        self,\n'
    '        request: Request,\n'
    '        credentials: HTTPAuthorizationCredentials | None = None,\n'
    '    ) -> dict[str, Any]:\n'
    '        from fastapi import HTTPException, Request\n'
    '        from fastapi.security import HTTPAuthorizationCredentials\n'
    '        """Authenticate a request.'
)
new = (
    '    async def authenticate_request(\n'
    '        self,\n'
    '        request: Request,\n'
    '        credentials: HTTPAuthorizationCredentials | None = None,\n'
    '    ) -> dict[str, Any]:\n'
    '        """Authenticate a request.'
)
assert old in content, f'Pattern 1 not found'
content = content.replace(old, new, 1)

# 3. Add lazy imports after the docstring closing triple-quote
old2 = (
    '            HTTPException: If authentication fails\n'
    '        """\n'
    '        if not self.config.enabled:'
)
new2 = (
    '            HTTPException: If authentication fails\n'
    '        """\n'
    '        from fastapi import HTTPException\n'
    '        from fastapi.security import HTTPAuthorizationCredentials\n'
    '        if not self.config.enabled:'
)
assert old2 in content, f'Pattern 2 not found'
content = content.replace(old2, new2, 1)

open('src/utils/auth.py', 'w').write(content)
print('done')
