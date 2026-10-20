#!/bin/bash
# Deploy the UI build (with the manual) and ffa-app to a station Pi.
# Run on a machine with Node, from anywhere inside the project:
#
#   ffa-app/tools/deploy/deploy-station.sh             build, back up, copy, pull, restart
#   ffa-app/tools/deploy/deploy-station.sh --dry-run   show what would change, touch nothing
#   ffa-app/tools/deploy/deploy-station.sh --no-build  deploy the dist that is already built
#   ffa-app/tools/deploy/deploy-station.sh --yes       don't ask before restarting
#
# The Pi has no Node and dist/ is not in git, so the build is made here and
# copied. Steps: build -> back up the station (dist + git heads) -> rsync dist
# -> git pull ffa-app and ffa-view -> docker compose restart ffa-app -> check.
#
# Station (override with env vars):
#   FFA_SSH_TARGET  suraj@raspberrypi-ssh.at.remote.it
#   FFA_SSH_PORT    33006
#   FFA_SSH_KEY     ~/.ssh/ffa_pi_ed25519
#   FFA_REMOTE_DIR  Documents/FFA-complete-project   (relative to the remote home)
#   FFA_REMOTE_UI   ffa-view                         (UI repo folder on the station)
set -eu -o pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
APP_DIR=$(cd "$HERE/../.." && pwd)
UI_DIR=${FFA_UI_DIR:-$(cd "$APP_DIR/../user-interface" 2>/dev/null && pwd || true)}
DIST="$APP_DIR/dist"

TARGET=${FFA_SSH_TARGET:-suraj@raspberrypi-ssh.at.remote.it}
PORT=${FFA_SSH_PORT:-33006}
KEY=${FFA_SSH_KEY:-$HOME/.ssh/ffa_pi_ed25519}
REMOTE_DIR=${FFA_REMOTE_DIR:-Documents/FFA-complete-project}
REMOTE_UI=${FFA_REMOTE_UI:-ffa-view}
SSH_OPTS="-i $KEY -p $PORT -o ServerAliveInterval=15 -o ConnectTimeout=20"

BUILD=1 DRY=0 YES=0
for arg in "$@"; do
    case "$arg" in
        --no-build) BUILD=0 ;;
        --dry-run) DRY=1 ;;
        --yes) YES=1 ;;
        -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

step() { printf '\n== %s\n' "$*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

# remote.it drops connections now and then; a retry is usually enough.
remote() {
    local try rc
    for try in 1 2 3; do
        # shellcheck disable=SC2086
        ssh $SSH_OPTS "$TARGET" "$@" && return 0
        rc=$?
        [ $rc -eq 255 ] || return $rc   # the command failed, not the connection
        echo "  connection failed, retrying ($try/3)..." >&2
        sleep 3
    done
    return 255
}

# ---------------------------------------------------------------- local checks
step "Local checks"
[ -f "$KEY" ] || die "SSH key not found: $KEY"
for repo in "$APP_DIR" ${UI_DIR:+"$UI_DIR"}; do
    name=$(basename "$repo")
    branch=$(git -C "$repo" rev-parse --abbrev-ref HEAD)
    git -C "$repo" fetch -q 2>/dev/null || echo "  $name: could not fetch, ahead/behind unknown"
    if ! git -C "$repo" merge-base --is-ancestor HEAD "@{u}" 2>/dev/null; then
        die "$name ($branch) has commits that are not pushed; the station pulls from the remote. Push first."
    fi
    echo "  $name: $branch @ $(git -C "$repo" rev-parse --short HEAD)"
done

if [ $BUILD -eq 1 ]; then
    [ -n "$UI_DIR" ] || die "user-interface repo not found next to ffa-app (set FFA_UI_DIR)"
    step "Build UI into $DIST"
    if [ $DRY -eq 1 ]; then echo "  (dry run: skipping build, using the current dist)"
    else (cd "$UI_DIR" && FFA_DIST="$DIST" npm run build --silent); fi
fi
[ -f "$DIST/index.html" ] || die "$DIST/index.html missing; run without --no-build"
[ -f "$DIST/manual/index.html" ] || echo "  warning: dist/manual is missing, /manual/ will be 404"

# --------------------------------------------------------------- station state
step "Station $TARGET"
remote "cd $REMOTE_DIR && for r in ffa-app $REMOTE_UI; do printf '  %-9s ' \$r; git -C \$r log --oneline -1; git -C \$r status --short | sed 's/^/      local: /'; done" \
    || die "cannot reach the station"

TS=$(date -u +%Y%m%dT%H%M%SZ)
if [ $DRY -eq 1 ]; then
    step "Dry run: files that would change in dist"
    # shellcheck disable=SC2086
    rsync -azn --delete --itemize-changes -e "ssh $SSH_OPTS" "$DIST/" "$TARGET:$REMOTE_DIR/ffa-app/dist/" | sed 's/^/  /' | head -60
    step "Dry run: commits the station would pull"
    remote "cd $REMOTE_DIR && for r in ffa-app $REMOTE_UI; do git -C \$r fetch -q && echo \"  \$r:\" && git -C \$r log --oneline HEAD..@{u} | sed 's/^/    /'; done"
    echo
    echo "Dry run only: nothing was changed."
    exit 0
fi

# ---------------------------------------------------------------------- backup
step "Back up the station to ~/ffa-backups/deploy-$TS"
remote "set -e; B=~/ffa-backups/deploy-$TS; mkdir -p \$B; cd $REMOTE_DIR
    tar -czf \$B/dist.tgz -C ffa-app dist
    for r in ffa-app $REMOTE_UI; do echo \"\$r \$(git -C \$r rev-parse HEAD)\" >> \$B/git-heads.txt; done
    echo \"  \$(du -sh \$B | cut -f1) saved\""

# ------------------------------------------------------------------ copy + pull
step "Copy dist"
# rsync resumes where a dropped connection left it; --partial keeps half-sent files.
copied=0
for try in 1 2 3 4 5; do
    # shellcheck disable=SC2086
    if out=$(rsync -az --partial --timeout=30 --delete --stats -e "ssh $SSH_OPTS" "$DIST/" "$TARGET:$REMOTE_DIR/ffa-app/dist/" 2>&1); then
        echo "$out" | grep -E 'Number of (regular )?files transferred|Total transferred file size' | sed 's/^/  /'
        copied=1; break
    fi
    echo "  copy interrupted, retrying ($try/5)..." >&2
    sleep 5
done
[ $copied -eq 1 ] || die "could not copy dist (connection). Nothing was pulled or restarted; run the script again. Backup in ~/ffa-backups/deploy-$TS"

step "Pull ffa-app and $REMOTE_UI (fast-forward only)"
rc=0
remote "set -e; cd $REMOTE_DIR; for r in ffa-app $REMOTE_UI; do echo \"  \$r:\"; git -C \$r pull -q --ff-only; git -C \$r log --oneline -1 | sed 's/^/    /'; done" || rc=$?
if [ $rc -eq 255 ]; then die "lost the connection during git pull; nothing restarted. Run the script again (--no-build). Backup in ~/ffa-backups/deploy-$TS"
elif [ $rc -ne 0 ]; then die "git pull failed on the station (local changes or diverged branch); nothing restarted. Backup in ~/ffa-backups/deploy-$TS"; fi

# --------------------------------------------------------------------- restart
step "Restart ffa-app"
if [ $YES -eq 0 ]; then
    printf '  The station is unavailable for a few seconds. Restart now? [y/N] '
    read -r answer
    case "$answer" in y|Y|yes|s|S|si) ;; *) echo "  Not restarted. Run later on the station: cd ~/$REMOTE_DIR && docker compose restart ffa-app"; exit 0 ;; esac
fi
remote "cd $REMOTE_DIR && docker compose restart ffa-app >/dev/null"

step "Check"
remote 'for i in $(seq 1 30); do
        code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3030/) || true
        [ "$code" = 200 ] && break; sleep 2; done
    app=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3030/)
    man=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3030/manual/)
    echo "  app: $app   manual: $man"
    [ "$app" = 200 ] && [ "$man" = 200 ]' \
    || die "the station did not answer correctly. Logs: docker logs --tail 50 ffa-complete-project-ffa-app-1 ; backup in ~/ffa-backups/deploy-$TS"

echo
echo "Deployed. Backup: ~/ffa-backups/deploy-$TS (dist.tgz, git-heads.txt)."
