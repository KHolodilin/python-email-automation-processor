# Security Policy

## Supported Versions

We actively support the following versions of the project with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 8.0.x   | :white_check_mark: |
| 7.x.x   | :white_check_mark: |
| < 7.0   | :x:                |

## Reporting a Vulnerability

We take the security of this project seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:

**kholodilin.valerii@gmail.com**

### What to Include

When reporting a vulnerability, please include:

- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact of the vulnerability
- Any suggested fixes or mitigations (if available)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your report within 48 hours
- **Initial Assessment**: We will provide an initial assessment within 7 days
- **Updates**: We will keep you informed of our progress
- **Resolution**: We will work to resolve the issue as quickly as possible

### Disclosure Policy

- We will work with you to understand and resolve the issue quickly
- We will not disclose the vulnerability publicly until a fix is available
- We will credit you for the discovery (unless you prefer to remain anonymous)
- We will coordinate the public disclosure with you

### Security Best Practices

When using this project, please follow these security best practices:

1. **Keep your dependencies up to date**: Regularly update the project and its dependencies
2. **Use secure password storage**: The project uses keyring for secure password storage - do not store passwords in plain text
3. **Review configuration files**: Ensure your `config.yaml` file has appropriate permissions and is not publicly accessible
4. **Use encryption**: Enable password encryption in the configuration when available
5. **Monitor logs**: Regularly review logs for suspicious activity
6. **Limit access**: Only grant access to trusted users and systems

### Known Security Considerations

- **Password Storage**: Passwords are stored using the system keyring (Windows Credential Manager, macOS Keychain, Linux SecretService). On first use, passwords are encrypted using system-based key derivation before storage.
- **File Permissions**: The project checks file permissions for password files on Unix systems and warns if permissions are too open.
- **Network Communication**: All IMAP and SMTP connections should use TLS/SSL encryption. Ensure your configuration uses secure connections.

### Security Updates

Security updates will be released as patch versions (e.g., 8.0.1 → 8.0.2) and will be documented in the release notes.

Thank you for helping keep this project and its users safe!
