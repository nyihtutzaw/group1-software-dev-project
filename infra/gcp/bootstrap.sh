#!/bin/sh
# One-time Google Cloud setup for the hosted CRVR class demo (see docs/deployment.md).
#
#   sh infra/gcp/bootstrap.sh
#
# Needs: gcloud signed in as a project Owner (use a separate gcloud configuration for this
# project), and openssl. Safe to re-run: anything that already exists is left as it is, and no
# secret value is ever printed. The Cloud Run service itself is created by the first deploy.
set -eu

# shellcheck source=infra/gcp/config.sh
. "$(dirname "$0")/config.sh"

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
exists() { "$@" >/dev/null 2>&1; }
# IAM bindings can fail for a few seconds after a service account is created; retry them.
retry() {
  n=0
  until "$@" >/dev/null; do
    n=$((n + 1))
    [ "$n" -ge 6 ] && return 1
    echo "  (retrying in 10 s)"
    sleep 10
  done
}

ACCOUNT=$(gcloud config get-value account 2>/dev/null)
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
echo "Project ${PROJECT_ID} (${PROJECT_NUMBER}) as ${ACCOUNT}, region ${REGION}"

step "Enable APIs"
gcloud services enable \
  run.googleapis.com sqladmin.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com iam.googleapis.com iamcredentials.googleapis.com \
  sts.googleapis.com cloudscheduler.googleapis.com cloudbilling.googleapis.com \
  billingbudgets.googleapis.com cloudresourcemanager.googleapis.com

step "Budget alert (${BUDGET_AMOUNT}/month; e-mails the billing admins at 50%, 90%, 100%)"
BILLING_ACCOUNT=$(gcloud billing projects describe "$PROJECT_ID" \
  --format='value(billingAccountName)' | sed 's|billingAccounts/||')
if gcloud billing budgets list --billing-account="$BILLING_ACCOUNT" \
  --format='value(displayName)' | grep -qx 'CRVR demo'; then
  echo "exists"
else
  gcloud billing budgets create --billing-account="$BILLING_ACCOUNT" \
    --display-name='CRVR demo' --budget-amount="$BUDGET_AMOUNT" \
    --filter-projects="projects/${PROJECT_ID}" \
    --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
fi

step "Artifact Registry: ${AR_REPO} (keeps the 3 newest images)"
exists gcloud artifacts repositories describe "$AR_REPO" --location="$REGION" ||
  gcloud artifacts repositories create "$AR_REPO" --location="$REGION" \
    --repository-format=docker --description="CRVR images"
gcloud artifacts repositories set-cleanup-policies "$AR_REPO" --location="$REGION" \
  --policy="$(dirname "$0")/artifact-cleanup.json" --no-dry-run >/dev/null

step "Cloud SQL: ${DB_INSTANCE} (PostgreSQL 17, db-f1-micro, 10 GB) — first run takes ~10 min"
exists gcloud sql instances describe "$DB_INSTANCE" ||
  gcloud sql instances create "$DB_INSTANCE" \
    --database-version=POSTGRES_17 --edition=ENTERPRISE --tier=db-f1-micro \
    --region="$REGION" --availability-type=zonal \
    --storage-type=SSD --storage-size=10 --no-storage-auto-increase \
    --backup-start-time=10:00 --retained-backups-count=3 \
    --deletion-protection
# A stopped instance cannot be changed: make sure it is running for the rest of the setup.
gcloud sql instances patch "$DB_INSTANCE" --activation-policy=ALWAYS --quiet >/dev/null
exists gcloud sql databases describe "$DB_NAME" --instance="$DB_INSTANCE" ||
  gcloud sql databases create "$DB_NAME" --instance="$DB_INSTANCE"

step "Secrets (generated here, never printed)"
if exists gcloud secrets describe crvr-database-url; then
  echo "crvr-database-url exists"
else
  DB_PASSWORD=$(openssl rand -hex 24)
  if gcloud sql users list --instance="$DB_INSTANCE" --format='value(name)' | grep -qx "$DB_USER"; then
    gcloud sql users set-password "$DB_USER" --instance="$DB_INSTANCE" --password="$DB_PASSWORD"
  else
    gcloud sql users create "$DB_USER" --instance="$DB_INSTANCE" --password="$DB_PASSWORD"
  fi
  printf 'postgresql+psycopg://%s:%s@/%s?host=/cloudsql/%s:%s:%s' \
    "$DB_USER" "$DB_PASSWORD" "$DB_NAME" "$PROJECT_ID" "$REGION" "$DB_INSTANCE" |
    gcloud secrets create crvr-database-url --data-file=- --replication-policy=automatic
  unset DB_PASSWORD
fi
exists gcloud secrets describe crvr-jwt-secret ||
  openssl rand -hex 32 | tr -d '\n' |
  gcloud secrets create crvr-jwt-secret --data-file=- --replication-policy=automatic
# The demo accounts' password, for the professor. Read it yourself with
#   gcloud secrets versions access latest --secret=crvr-demo-password
exists gcloud secrets describe crvr-demo-password ||
  openssl rand -base64 30 | tr -dc 'A-Za-z0-9' | cut -c1-16 |
  gcloud secrets create crvr-demo-password --data-file=- --replication-policy=automatic

step "Evidence bucket: gs://${BUCKET} (private)"
exists gcloud storage buckets describe "gs://${BUCKET}" ||
  gcloud storage buckets create "gs://${BUCKET}" --location="$REGION" \
    --uniform-bucket-level-access --public-access-prevention

step "Service accounts"
for sa in "crvr-run:CRVR Cloud Run runtime" \
  "crvr-deployer:CRVR GitHub Actions deployer" \
  "crvr-db-scheduler:CRVR Cloud SQL start-stop"; do
  name=${sa%%:*}
  exists gcloud iam service-accounts describe "${name}@${PROJECT_ID}.iam.gserviceaccount.com" ||
    gcloud iam service-accounts create "$name" --display-name="${sa#*:}"
done

step "Permissions"
project_role() {
  retry gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$1" --role="$2" --condition=None --quiet
  echo "  $2 → ${1%%@*}"
}
# The app: connect to Cloud SQL, read its three secrets, read/write evidence files.
project_role "$RUN_SA" roles/cloudsql.client
for secret in crvr-database-url crvr-jwt-secret crvr-demo-password; do
  retry gcloud secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:${RUN_SA}" --role=roles/secretmanager.secretAccessor
done
retry gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${RUN_SA}" --role=roles/storage.objectUser
echo "  secrets + bucket → crvr-run"
# GitHub Actions: push images, deploy Cloud Run, start/stop the database, pause the schedule.
project_role "$DEPLOY_SA" roles/run.admin
project_role "$DEPLOY_SA" roles/cloudsql.editor
project_role "$DEPLOY_SA" roles/cloudscheduler.admin
retry gcloud artifacts repositories add-iam-policy-binding "$AR_REPO" --location="$REGION" \
  --member="serviceAccount:${DEPLOY_SA}" --role=roles/artifactregistry.writer
retry gcloud iam service-accounts add-iam-policy-binding "$RUN_SA" \
  --member="serviceAccount:${DEPLOY_SA}" --role=roles/iam.serviceAccountUser
echo "  image push + act as crvr-run → crvr-deployer"
# Cloud Scheduler: start/stop the database only.
project_role "$SCHEDULER_SA" roles/cloudsql.editor

step "GitHub keyless sign-in (Workload Identity Federation; main branch of ${GITHUB_REPO} only)"
exists gcloud iam workload-identity-pools describe github --location=global ||
  gcloud iam workload-identity-pools create github --location=global \
    --display-name="GitHub Actions"
exists gcloud iam workload-identity-pools providers describe crvr-repo \
  --workload-identity-pool=github --location=global ||
  gcloud iam workload-identity-pools providers create-oidc crvr-repo \
    --workload-identity-pool=github --location=global \
    --display-name="CRVR repository" \
    --issuer-uri=https://token.actions.githubusercontent.com \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository == '${GITHUB_REPO}' && assertion.ref == 'refs/heads/main'"
POOL="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github"
retry gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/${POOL}/attribute.repository/${GITHUB_REPO}"
echo "  ${GITHUB_REPO}@main → crvr-deployer"

step "Database schedule: stop ${DB_STOP_CRON}, start ${DB_START_CRON} (${TIME_ZONE})"
SQL_API="https://sqladmin.googleapis.com/v1/projects/${PROJECT_ID}/instances/${DB_INSTANCE}"
# Scheduler cannot send PATCH (what instances.patch needs): POST + X-HTTP-Method-Override.
schedule() { # name cron activation-policy
  if exists gcloud scheduler jobs describe "$1" --location="$REGION"; then
    verb=update
    headers=--update-headers=Content-Type=application/json,X-HTTP-Method-Override=PATCH
  else
    verb=create
    headers=--headers=Content-Type=application/json,X-HTTP-Method-Override=PATCH
  fi
  gcloud scheduler jobs "$verb" http "$1" --location="$REGION" \
    --schedule="$2" --time-zone="$TIME_ZONE" \
    --http-method=POST --uri="$SQL_API" "$headers" \
    --message-body="{\"settings\":{\"activationPolicy\":\"$3\"}}" \
    --oauth-service-account-email="$SCHEDULER_SA" \
    --oauth-token-scope=https://www.googleapis.com/auth/cloud-platform >/dev/null
  echo "  $1 ($verb)"
}
schedule crvr-db-stop "$DB_STOP_CRON" NEVER
schedule crvr-db-start "$DB_START_CRON" ALWAYS

step "Done. GitHub repository variables (not secrets) for the deploy workflow:"
cat <<EOF
  GCP_WIF_PROVIDER = ${POOL}/providers/crvr-repo
  GCP_DEPLOYER_SA  = ${DEPLOY_SA}

  gh variable set GCP_WIF_PROVIDER --body "${POOL}/providers/crvr-repo"
  gh variable set GCP_DEPLOYER_SA --body "${DEPLOY_SA}"

Demo password for the professor (run it yourself; it is not shown here):
  gcloud secrets versions access latest --secret=crvr-demo-password
EOF
