#!/bin/sh
# Deploy one image to the hosted demo: migrate + seed, then roll out the web service.
#
#   sh infra/gcp/deploy.sh <image>        e.g. …/crvr/crvr:<git sha>
#   sh infra/gcp/deploy.sh <image> reset  wipe the demo data first (Reset demo data workflow)
#
# Normally run by GitHub Actions (.github/workflows/deploy.yml). If the database is stopped for
# the night it is started for the migration and stopped again afterwards.
set -eu

# shellcheck source=infra/gcp/config.sh
. "$(dirname "$0")/config.sh"
CLOUDRUN="$(dirname "$0")/../cloudrun"
IMAGE=${1:?usage: deploy.sh <image> [reset]}
ACTION=${2:-migrate}
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

render() { # template → rendered file with names from config.sh
  sed -e "s|__IMAGE__|${IMAGE}|g" -e "s|__PROJECT_ID__|${PROJECT_ID}|g" \
    -e "s|__REGION__|${REGION}|g" -e "s|__SERVICE__|${SERVICE}|g" -e "s|__JOB__|${JOB}|g" \
    -e "s|__DB_INSTANCE__|${DB_INSTANCE}|g" -e "s|__RUN_SA__|${RUN_SA}|g" \
    -e "s|__BUCKET__|${BUCKET}|g" "$1" >"$2"
  if grep -q '__[A-Z_]*__' "$2"; then
    echo "unfilled placeholder in $1" >&2
    exit 1
  fi
}

echo "== Database"
sh "$(dirname "$0")/power.sh" on

echo "== Job ${JOB}: ${ACTION}"
render "$CLOUDRUN/job.yaml" "$WORK/job.yaml"
gcloud run jobs replace "$WORK/job.yaml" --region="$REGION" --quiet >/dev/null
if [ "$ACTION" = reset ]; then
  gcloud run jobs execute "$JOB" --region="$REGION" --wait \
    --args=scripts/cloud-run-job.sh,reset --update-env-vars=CONFIRM_RESET=wipe-demo-data
else
  gcloud run jobs execute "$JOB" --region="$REGION" --wait
fi

echo "== Service ${SERVICE}"
render "$CLOUDRUN/service.yaml" "$WORK/service.yaml"
gcloud run services replace "$WORK/service.yaml" --region="$REGION" --quiet
# A public website: anyone may open it (signing in is still required for everything private).
gcloud run services add-iam-policy-binding "$SERVICE" --region="$REGION" \
  --member=allUsers --role=roles/run.invoker --quiet >/dev/null

URL=$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')
echo "== Live: ${URL}"
curl -fsS --retry 5 --retry-delay 3 --retry-all-errors "${URL}/api/health" && echo

echo "== Night check"
sh "$(dirname "$0")/power.sh" follow
