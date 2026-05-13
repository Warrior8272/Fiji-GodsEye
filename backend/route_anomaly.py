import math

COURSE_CHANGE_THRESHOLD = 45
SPEED_DROP_THRESHOLD = 12


def calculate_course_change(old, new):

    try:
        diff = abs(float(new) - float(old))

        if diff > 180:
            diff = 360 - diff

        return diff

    except:
        return 0


def process_route_anomalies(vessels):

    alerts = []

    for vessel in vessels:

        previous_course = vessel.get("previous_course")
        current_course = vessel.get("course")

        previous_speed = vessel.get("previous_speed")
        current_speed = vessel.get("speed")

        if previous_course is not None and current_course is not None:

            change = calculate_course_change(
                previous_course,
                current_course
            )

            if change >= COURSE_CHANGE_THRESHOLD:

                alerts.append({
                    "type": "ROUTE_ANOMALY",
                    "risk": "MEDIUM",
                    "mmsi": vessel.get("mmsi"),
                    "vessel": vessel.get("shipname"),
                    "course_change": round(change, 2),
                    "msg": f"Large course deviation detected ({round(change,2)}°)"
                })

        try:

            if (
                previous_speed is not None and
                current_speed is not None
            ):

                drop = float(previous_speed) - float(current_speed)

                if drop >= SPEED_DROP_THRESHOLD:

                    alerts.append({
                        "type": "SPEED_ANOMALY",
                        "risk": "MEDIUM",
                        "mmsi": vessel.get("mmsi"),
                        "vessel": vessel.get("shipname"),
                        "speed_drop": round(drop, 2),
                        "msg": f"Sudden speed reduction detected ({round(drop,2)} knots)"
                    })

        except:
            pass

    return alerts
