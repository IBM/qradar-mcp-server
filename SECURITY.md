# Security Policy

## Reporting Security Vulnerabilities

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability in this project, please report it privately to help us address it responsibly.

### How to Report

1. **Email:** <ashrivastava@ibm.com>
2. **Subject:** [SECURITY] QRadar MCP Server - Brief Description
3. **Include:**
   - Type of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

### Response Timeline

- **Acknowledgment:** Within 48 hours
- **Initial Assessment:** Within 5 business days
- **Resolution:** Varies by severity (critical issues prioritized)

### Security Best Practices

When deploying this project:

1. **Credentials Management**
   - Never commit API tokens, passwords, or secrets to version control
   - Use environment variables for sensitive data
   - Rotate QRadar API tokens regularly

2. **Network Security**
   - Use SSL/TLS for QRadar connections (`QRADAR_VERIFY_SSL=true`)
   - Bind HTTP server to localhost (`127.0.0.1`) when not needed externally

3. **Access Control**
   - Use QRadar API tokens with minimum required permissions
   - Implement rate limiting for API endpoints
   - Monitor and audit tool execution logs

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| < 2.0   | :x:                |

## Known Security Considerations

- This is a development/demonstration project (MVP status)
- Not recommended for production use without thorough security review
- No built-in authentication for HTTP endpoints
- Logs may contain sensitive QRadar data

## Disclaimer

This code is provided as-is under the Apache 2.0 license. IBM makes no warranties regarding security and is under no obligation to provide security updates or support.
