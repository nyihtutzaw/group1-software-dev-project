#!/bin/sh
# Turn the hosted demo's database on/off and control its overnight schedule.
#
#   sh infra/gcp/power.sh status   is the database running? is the schedule active?
#   sh infra/gcp/power.sh on       start the database now (takes 1–2 minutes)
#   sh infra/gcp/power.sh off      stop it now (the site shows "closed" until it is started)
#   sh infra/gcp/power.sh hold     pause the 23:00/06:00 schedule (late demo, holidays)
#   sh infra/gcp/power.sh auto     resume the schedule
#   sh infra/gcp/power.sh follow   stop it if it is closing time and the schedule is active
#                                  (used after a night-time deploy had to start it)
#
# The same actions run from GitHub: Actions → "Demo power" → Run workflow.
# Note: the 06:00 start also undoes a manual "off" — use "hold" to keep it off for days.
set -eu

# shellcheck source=infra/gcp/config.sh
. "$(dirname "$0")/config.sh"

state() {
  gcloud sql instances describe "$DB_INSTANCE" --format='value(settings.activationPolicy,state)'
}
schedule_state() {
  gcloud scheduler jobs describe crvr-db-stop --location="$REGION" --format='value(state)'
}
set_policy() {
  gcloud sql instances patch "$DB_INSTANCE" --activation-policy="$1" --quiet >/dev/null
}

case "${1:-status}" in
  status)
    echo "database: $(state | tr '\t' ' ')   (ALWAYS RUNNABLE = on, NEVER STOPPED = off)"
    echo "schedule: $(schedule_state)   (ENABLED = off ${CLOSED_FROM_HOUR}:00–0${OPEN_FROM_HOUR}:00 \
${TIME_ZONE}; PAUSED = held)"
    ;;
  on)
    echo "Starting ${DB_INSTANCE} (1–2 minutes)…"
    set_policy ALWAYS
    echo "database: $(state | tr '\t' ' ')"
    ;;
  off)
    echo "Stopping ${DB_INSTANCE}…"
    set_policy NEVER
    echo "database: $(state | tr '\t' ' ')"
    ;;
  hold)
    gcloud scheduler jobs pause crvr-db-stop --location="$REGION" >/dev/null
    gcloud scheduler jobs pause crvr-db-start --location="$REGION" >/dev/null
    echo "schedule: PAUSED — the database stays as it is now ($(state | cut -f1)) until 'auto'"
    ;;
  auto)
    gcloud scheduler jobs resume crvr-db-stop --location="$REGION" >/dev/null
    gcloud scheduler jobs resume crvr-db-start --location="$REGION" >/dev/null
    echo "schedule: ENABLED"
    ;;
  follow)
    hour=$(TZ="$TIME_ZONE" date +%H | sed 's/^0//')
    if [ "$(schedule_state)" = ENABLED ] &&
      { [ "$hour" -ge "$CLOSED_FROM_HOUR" ] || [ "$hour" -lt "$OPEN_FROM_HOUR" ]; }; then
      echo "Closing hours (${hour}:00 ${TIME_ZONE}) — stopping the database again."
      set_policy NEVER
    else
      echo "Open hours or schedule on hold — leaving the database running."
    fi
    ;;
  *)
    sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
