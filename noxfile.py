"""Nox sessions for linting, sanity, and security checks."""

import nox

nox.options.sessions = ["lint", "security"]


@nox.session(python="3.12")
def lint(session):
    """Run ansible-lint."""
    session.install("ansible-lint")
    session.run("ansible-lint")


@nox.session(python="3.12")
def security(session):
    """Run bandit security scanner."""
    session.install("bandit")
    session.run("bandit", "-r", "plugins/", "-ll", "-ii")
