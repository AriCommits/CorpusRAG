---
name: security-audit
description: Reviews code/architecture for vulnerabilities and saves the report with an auto-incrementing filename.
---

# Security Audit Skill

When asked to perform a security audit, act as a Senior DevSecOps Engineer.

## Step 1: Analyze and Hunt
Review the code, files, or architecture specified by the user. You must actively look for:
- OWASP Top 10 vulnerabilities (Injection, Broken Auth, etc.)
- Hardcoded secrets or API key leaks
- Poor error handling that exposes stack traces
- Insecure dependencies or outdated practices
- Logical flaws in business logic

## Step 2: Format the Report
Draft your findings in Markdown. For every vulnerability found, you MUST include:
1. **Severity:** (Critical, High, Medium, Low)
2. **Description:** What the vulnerability is and how it can be exploited.
3. **Remediation:** Explicit code or architecture fixes to resolve the issue.

## Step 3: Determine File Path
Run the following command in `bash` to get the target file path:
`python3 ~/.config/opencode/skills/security-audit/get_next_audit.py`

## Step 4: Save the File
Read the output from the script in Step 3. That output is your exact target file path (e.g., `.opencode/security/security-audit-001.md`). 
Write your Markdown plan from Step 1 directly to that file path using your file writing tool. Confirm with the user once the file is saved, highlighting any "Critical" or "High" severity issues immediately in the chat.