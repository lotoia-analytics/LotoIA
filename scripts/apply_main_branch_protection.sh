#!/usr/bin/env bash
# Aplica proteção institucional da branch main via GitHub API.
# Requer token com permissão admin no repositório (gh auth login como owner/admin).
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-lotoia-analytics/LotoIA}"
BRANCH="${PROTECTED_BRANCH:-main}"

echo "Applying branch protection to ${REPO}:${BRANCH} ..."

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${REPO}/branches/${BRANCH}/protection" \
  -f required_status_checks[strict]=true \
  -f required_status_checks[contexts][]=lint \
  -f required_status_checks[contexts][]=tests \
  -f required_status_checks[contexts][]=governance-contract-check \
  -f required_status_checks[contexts][]=lei15-lei15a-boundary-check \
  -f required_status_checks[contexts][]=dashboard-semantic-label-check \
  -f enforce_admins=true \
  -f required_pull_request_reviews[dismiss_stale_reviews]=true \
  -f required_pull_request_reviews[require_code_owner_reviews]=true \
  -f required_pull_request_reviews[required_approving_review_count]=1 \
  -f required_linear_history=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false \
  -f required_conversation_resolution=true \
  -f restrictions=

echo "Branch protection applied."
echo "Verify at: https://github.com/${REPO}/settings/branches"
