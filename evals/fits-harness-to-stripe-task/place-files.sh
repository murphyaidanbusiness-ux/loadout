#!/usr/bin/env bash
# Copies the sample project in. Two files are stored under other names so the repo that holds this test
# does not treat them as its own: the project's .gitignore, and a .env.local of fake keys.
set -eu
cp -R "$(dirname "$0")/files/." .
mv gitignore.fixture .gitignore
mv env.local.fixture .env.local
