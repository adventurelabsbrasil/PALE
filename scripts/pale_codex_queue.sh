#!/bin/bash
# Run the remaining PALE tickets as fresh, ordered Codex sessions.
# This runner pushes one integration branch and opens one final PR; it never merges.
set -u

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="origin"
QUEUE_BRANCH="codex/pale-queue"
ISSUES="5 6 7 8 9"
QUEUE_DIR="$REPO_DIR/artifacts/pale-queue"
STATE_DIR="$QUEUE_DIR/state"
LOCK_DIR="$QUEUE_DIR/lock"
LOG_DIR="$QUEUE_DIR/logs"

mkdir -p "$STATE_DIR" "$LOG_DIR"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "PALE queue already running: $LOCK_DIR" >&2
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

git_cmd() {
  GIT_OPTIONAL_LOCKS=0 git -C "$REPO_DIR" "$@"
}

fail() {
  echo "PALE queue stopped: $*" >&2
  exit 1
}

git_cmd fetch "$REMOTE" || fail "git fetch failed"
if [ -n "$(git_cmd status --porcelain)" ]; then
  fail "worktree is not clean before queue start"
fi

if git_cmd show-ref --verify --quiet "refs/heads/$QUEUE_BRANCH"; then
  git_cmd switch "$QUEUE_BRANCH" || fail "could not switch to $QUEUE_BRANCH"
else
  git_cmd switch -c "$QUEUE_BRANCH" "$REMOTE/main" || fail "could not create $QUEUE_BRANCH"
fi
git_cmd merge --ff-only "$REMOTE/main" || fail "queue branch is not based on current origin/main"

for issue in $ISSUES; do
  marker="$STATE_DIR/$issue.done"
  if [ -f "$marker" ]; then
    echo "PALE #$issue already completed; continuing"
    continue
  fi

  if [ -n "$(git_cmd status --porcelain)" ]; then
    fail "worktree became dirty before PALE #$issue"
  fi

  issue_url="https://github.com/adventurelabsbrasil/PALE/issues/$issue"
  log_file="$LOG_DIR/issue-$issue.log"
  message_file="$LOG_DIR/issue-$issue.last-message.md"
  prompt="$(cat <<EOF
You are one fresh Codex worker in a sequential PALE implementation queue.

Work only on GitHub issue $issue_url. The current repository is the PALE umbrella project and the current branch is $QUEUE_BRANCH. Do not switch branches.

Read the repository instructions and the complete issue before editing. Implement the issue end-to-end, preserve existing experiments, run the relevant tests, and perform a final diff/secret review.

This is an integration queue: do not merge, do not create a PR, do not run launchctl, and do not push. Commit all implementation changes locally with a clear Conventional Commit message containing "PALE queue #$issue" and the trailer:
Co-Authored-By: Codex · Star Command <codex@adventurelabs.com.br>

Leave the worktree clean and committed. Do not modify unrelated tickets. In your final response, summarize changes, tests, commit hash, and any blocker.
EOF
  )"

  echo "Starting fresh Codex session for PALE #$issue"
  if ! codex exec \
    --dangerously-bypass-approvals-and-sandbox \
    -C "$REPO_DIR" \
    -o "$message_file" \
    "$prompt" >"$log_file" 2>&1; then
    fail "Codex session failed for PALE #$issue; see $log_file"
  fi

  [ "$(git_cmd branch --show-current)" = "$QUEUE_BRANCH" ] || fail "worker changed the queue branch"
  [ -z "$(git_cmd status --porcelain)" ] || fail "worker left uncommitted changes for PALE #$issue; see $log_file"
  git_cmd log -1 --format=%B | grep -q "PALE queue #$issue" || fail "latest commit is not tagged for PALE #$issue"
  git_cmd push "$REMOTE" "$QUEUE_BRANCH" || fail "push failed after PALE #$issue"
  date -u "+%Y-%m-%dT%H:%M:%SZ" > "$marker"
  echo "Completed and pushed PALE #$issue"
done

final_pr="$QUEUE_DIR/final-pr.md"
if ! env -u GH_TOKEN -u GITHUB_TOKEN gh pr list -R adventurelabsbrasil/PALE --state open --head "$QUEUE_BRANCH" --json number --jq 'length' | grep -q '^0$'; then
  echo "Final PALE queue PR already exists; queue complete"
  exit 0
fi

cat > "$final_pr" <<'EOF'
## O que entra

Implementa sequencialmente as issues PALE-004 até PALE-008 na branch de integração do Codex.

Cada ticket foi executado por uma sessão fresca, com testes e commit próprios. Este PR concentra a integração final para que o Founder faça um único merge.

## Verificação

Os logs de cada sessão estão em `artifacts/pale-queue/logs/` localmente. O último worker deve deixar a suíte completa verde e o worktree limpo.

Closes #5
Closes #6
Closes #7
Closes #8
Closes #9

---

<sub><img src="https://app.adventurelabs.com.br/agents/star-command.png" width="16" height="16" align="top"> Generated with <a href="https://adventurelabs.com.br">Star Command</a> by Adventure Labs · <em>agente: Codex · Star Command</em></sub>
EOF

env -u GH_TOKEN -u GITHUB_TOKEN gh pr create \
  -R adventurelabsbrasil/PALE \
  --base main \
  --head "$QUEUE_BRANCH" \
  --title "PALE queue: concluir o primeiro corte audiovisual" \
  --body-file "$final_pr"
echo "PALE queue complete; final PR created"
