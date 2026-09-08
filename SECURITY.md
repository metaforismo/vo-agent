# Security Policy

## Reporting Issues

Please report suspected vulnerabilities through GitHub Security Advisories:

https://github.com/Limes-Labs/limes-quaestio/security/advisories/new

Use public issues only for non-sensitive bugs.

## Secret Handling

Limes Quaestio bundles are intended to be inspectable and shareable. Do not put secret
values in workflow state, message metadata, environment metadata, artifacts, or
reports.

Environment specs may include `secret_names`, but should never include secret
values. Tests should verify this whenever secret-related behavior changes.

## Local Artifacts

Generated bundles, reports, local scripts, and virtual environments belong in
`work/`, which is ignored by git.
