#!/bin/bash

# Script to simulate different users committing to git repository
# Sets name and email in local configuration
# Without arguments, the local name and email is unset

set -e

if [ $# -ne 1 ]; then
    git config --local --unset user.name
    git config --local --unset user.email
    echo "Local name and email unset."
    exit
fi
name=$1
email=$(echo "${name}" | tr '[:upper:]' '[:lower:]')"@example.com"

git config --local user.name "${name}"
git config --local user.email "${email}"
echo "Local name and email set to: ${name}, ${email}"
