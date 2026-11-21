#!/usr/bin/env bash

echo "$(date) - grab_booking.sh executed" > /config/scripts/grab_link.log

set -o pipefail

INPUT="$1"

if [[ -z "$INPUT" ]]; then
    echo '{"error":"No Grab message supplied"}'
    exit 1
fi

# --------------------------------------------------
# Extract Grab short URL from arbitrary text
#
# Example:
# Track my order... [https://app.grab.com/s/QN3E7Rna](...)
#
# Produces:
# https://app.grab.com/s/QN3E7Rna
# --------------------------------------------------

SHARE_URL=$(printf '%s\n' "$INPUT" |
    grep -oE 'https://app\.grab\.com/s/[A-Za-z0-9_-]+' |
    head -n 1)

if [[ -z "$SHARE_URL" ]]; then
    echo '{"error":"No Grab share URL found"}'
    exit 1
fi

# --------------------------------------------------
# Resolve Grab short URL
# --------------------------------------------------

LOCATION=$(curl -sS \
    -D - \
    -o /dev/null \
    "$SHARE_URL" 2>/dev/null |
    tr -d '\r' |
    grep -i '^location:' |
    head -n 1 |
    sed -E 's/^[Ll]ocation:[[:space:]]*//')

if [[ -z "$LOCATION" ]]; then
    echo '{"error":"Grab short URL did not return a redirect"}'
    exit 1
fi

# --------------------------------------------------
# Extract booking/share ID
# --------------------------------------------------

BOOKING_ID=$(printf '%s\n' "$LOCATION" |
    sed -n 's/.*[?&]shareOrderLink=\([^&]*\).*/\1/p' |
    head -n 1)

if [[ -z "$BOOKING_ID" ]]; then
    echo '{"error":"Could not extract Grab booking ID"}'
    exit 1
fi

# --------------------------------------------------
# Query Grab API
# --------------------------------------------------

API_URL="https://api.grab.com/api/v1/safety/sharemyride/${BOOKING_ID}/bookingdetails?fullData=false"

RESPONSE=$(curl -sS --fail \
    --url "$API_URL" \
    -H 'accept: application/json, text/plain, */*' \
    -H 'accept-language: en-US,en;q=0.9' \
    -H 'origin: https://sharelocation.grab.com' \
    -H 'user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36')

if [[ -z "$RESPONSE" ]]; then
    echo '{"error":"Grab API returned no data"}'
    exit 1
fi

# --------------------------------------------------
# Make sure jq is available
# --------------------------------------------------

if ! command -v jq >/dev/null 2>&1; then
    echo '{"error":"jq is not installed"}'
    exit 1
fi

# --------------------------------------------------
# Output clean JSON for Home Assistant
# --------------------------------------------------

echo "$RESPONSE" | jq \
    --arg share_url "$SHARE_URL" \
    --arg booking_id "$BOOKING_ID" \
    '
    {
        share_url: $share_url,
        booking_id: $booking_id,

        booking_code: (.booking.bookingCode // null),
        booking_state: (.booking.bookingState // null),

        driver_arrival_utc: (.booking.driverArrivalTime // null),

        route_eta_unix: (.route.ETA // null),

        title: (.messageStatus.title // null),   
        message: (.messageStatus.processMsg.message // null),

        is_pending_delivery:
            (.additionalOrderDetail.isPendingDelivery // null),

        driver_name: (.driver.name // null),
        vehicle_model: (.driver.vehicleModel // null),
        vehicle_plate: (.driver.vehiclePlateNumber // null),

        pickup: (.booking.pickup.keywords // null),
        dropoff: (.booking.dropOff.keywords // null)
    }
    '
