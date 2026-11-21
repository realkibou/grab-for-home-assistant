# Legacy YAML / bash setup

This folder contains the original implementation this integration was built
from. It still works if you configure it manually, but the custom integration in
`custom_components/grab_link` is the supported path.

## Files

| File | Purpose |
| --- | --- |
| `grab_link.sh` | Bash script: extracts the Grab share link, resolves it, calls the Grab API and prints JSON |
| `command_line_sensors.yaml` | `command_line` sensor that runs the script with the contents of `input_text.grab_link_share_message` |
| `template_sensors.yaml` | Template sensors derived from `sensor.grab_link_booking` |

## Setup

1. Copy `grab_link.sh` to `/config/scripts/grab_link.sh` and make it
   executable (`chmod +x`).
2. Create an `input_text` helper named `grab_link_share_message`.
3. Add the contents of `command_line_sensors.yaml` to your `command_line:`
   configuration and `template_sensors.yaml` under `template:`.
4. Reload YAML / restart Home Assistant.
5. Paste a Grab share message into the helper.

Requirements: `jq`, `curl` and `grep`/`sed` available in the Home Assistant
environment (the Home Assistant OS container includes them).

> The integration supersedes this setup: no shell script, no `input_text`
> round-trip, and sensors are created natively. The attribute names on
> `sensor.grab_link_booking` are identical, so both can coexist during a
> migration.
