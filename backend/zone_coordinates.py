ZONE_COORDS = {
    "Suva Port": {
        "lat": -18.1416,
        "lon": 178.4419,
        "zoom": 11
    },

    "Lautoka / Nadi": {
        "lat": -17.6100,
        "lon": 177.4500,
        "zoom": 10
    },

    "Western Fiji": {
        "lat": -17.8000,
        "lon": 177.7000,
        "zoom": 8
    },

    "Vanua Levu": {
        "lat": -16.7000,
        "lon": 179.3000,
        "zoom": 8
    },

    "Lau / Eastern Fiji": {
        "lat": -18.2000,
        "lon": -178.8000,
        "zoom": 7
    }
}

def get_zone_coordinates(zone):
    return ZONE_COORDS.get(zone)
