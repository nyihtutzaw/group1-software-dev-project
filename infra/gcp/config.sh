# Names shared by the Google Cloud scripts and GitHub Actions workflows (sourced, not run).
# shellcheck disable=SC2034  # sourced by the other scripts, which use these names
# Only names live here; secrets are generated straight into Secret Manager by bootstrap.sh.

PROJECT_ID=zaw-personal-project
REGION=asia-southeast1
GITHUB_REPO=nyihtutzaw/group1-software-dev-project

SERVICE=crvr                       # Cloud Run service (API + frontend)
JOB=crvr-tasks                     # Cloud Run job: migrate + seed (and reset on demand)
AR_REPO=crvr                       # Artifact Registry repository
DB_INSTANCE=crvr-db                # Cloud SQL for PostgreSQL 17 (+ PostGIS)
DB_NAME=crvr
DB_USER=crvr_app
BUCKET="${PROJECT_ID}-crvr-evidence"

RUN_SA="crvr-run@${PROJECT_ID}.iam.gserviceaccount.com"            # what the app runs as
DEPLOY_SA="crvr-deployer@${PROJECT_ID}.iam.gserviceaccount.com"    # what GitHub Actions uses
SCHEDULER_SA="crvr-db-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"

# The database is stopped overnight to save cost (Cloud Scheduler, Bangkok time).
TIME_ZONE=Asia/Bangkok
DB_STOP_CRON="0 23 * * *"
DB_START_CRON="0 6 * * *"
CLOSED_FROM_HOUR=23
OPEN_FROM_HOUR=6

BUDGET_AMOUNT=500THB               # monthly budget alert (the billing account is in THB)

IMAGE_REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/crvr"

# Every gcloud call in these scripts targets this project, whatever the active configuration says.
export CLOUDSDK_CORE_PROJECT="$PROJECT_ID"
