# Security Policy

## Reporting Issues

This repository does not yet have a public security contact. If you publish it,
add a private reporting address before accepting external use.

## Secret Handling

VO Agent bundles are intended to be inspectable and shareable. Do not put secret
values in workflow state, message metadata, environment metadata, artifacts, or
reports.

Environment specs may include `secret_names`, but should never include secret
values. Tests should verify this whenever secret-related behavior changes.

## Local Artifacts

Generated bundles, reports, local scripts, and virtual environments belong in
`work/`, which is ignored by git.
