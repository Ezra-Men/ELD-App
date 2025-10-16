from django.http import JsonResponse
from rest_framework.decorators import api_view
import requests
import json
from datetime import datetime, timedelta
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from geopy.distance import distance as geo_distance
from collections import defaultdict
from decouple import config
import time


# ===============================================================
# API VIEW: create_trip
# ---------------------------------------------------------------
# Accepts trip inputs (current, pickup, dropoff, cycle hours),
# computes routes (current->pickup & pickup->dropoff) using
# OpenRouteService, simulates Hours-of-Service events (FMCSA),
# generates ELD daily log images, and returns JSON with route
# geometry, stops, and base64 PNG log images.
# ===============================================================
@api_view(['POST'])
def create_trip(request):
    # -----------------------
    # Extract request payload
    # -----------------------
    data = request.data
    current_location = data.get('currentLocation')
    pickup_location = data.get('pickupLocation')
    dropoff_location = data.get('dropoffLocation')
    cycle_hours = float(data.get('cycleHours', 0))

    print(f"DEBUG: Processing locations - Current: {current_location}, Pickup: {pickup_location}, Dropoff: {dropoff_location}")

    # ------------------------------------------------------------
    # Helper: geocode(location) -> (lat, lon) or None
    # Uses Nominatim (OpenStreetMap) to convert location names to coords.
    # Adds a slight bias to USA if user didn't specify a country (helpful
    # for recruiter U.S. tests) and enforces Nominatim's 1 request/sec rule.
    # ------------------------------------------------------------
    def geocode(location):
        if "," not in location:
            # If user omitted country, bias toward USA for common test cases.
            location = f"{location}, USA"

        url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1"
        headers = {"User-Agent": "EzraTripPlannerAssessment/1.0 (contact: example@example.com)"}
        response = requests.get(url, headers=headers, timeout=10)

        # Respect Nominatim rate limit (1 request/sec)
        time.sleep(1.1)

        if response.status_code != 200:
            # Log and return None so caller can report which locations failed.
            print(f"Geocode failed for {location}: {response.status_code}")
            return None

        results = response.json()
        if results:
            lat, lon = float(results[0]["lat"]), float(results[0]["lon"])
            return lat, lon

        # No results found for the query
        print(f"Geocode returned empty for {location}")
        return None

    # ------------------------------------------------------------
    # Geocode input locations (current, pickup, dropoff)
    # If any fail, return 400 with which ones were invalid.
    # ------------------------------------------------------------
    current_coords = geocode(current_location)
    pickup_coords = geocode(pickup_location)
    dropoff_coords = geocode(dropoff_location)

    if not all([current_coords, pickup_coords, dropoff_coords]):
        missing = []
        if not current_coords: missing.append('current')
        if not pickup_coords: missing.append('pickup')
        if not dropoff_coords: missing.append('dropoff')
        return JsonResponse({'error': f'Invalid locations: {", ".join(missing)}'}, status=400)

    # ------------------------------------------------------------
    # Load OpenRouteService API key from environment
    # ------------------------------------------------------------
    ors_api_key = config('OPENROUTESERVICE_API_KEY')
    print(f"DEBUG: API Key loaded: {'YES' if ors_api_key else 'NO'} (first 5 chars: {ors_api_key[:5] if ors_api_key else 'None'})")

    if not ors_api_key:
        return JsonResponse({'error': 'OpenRouteService API key not configured'}, status=500)

    url = 'https://api.openrouteservice.org/v2/directions/driving-car'
    headers = {
        'Authorization': f'Bearer {ors_api_key}',
        'Content-Type': 'application/json'
    }

    # ============================================================
    # 1) Request route: current -> pickup
    #    Build request body with coordinates in [lon, lat] order.
    # ============================================================
    body1 = {
        'coordinates': [[current_coords[1], current_coords[0]], [pickup_coords[1], pickup_coords[0]]]
    }

    print("DEBUG: Making API call for current -> pickup")
    response1 = requests.post(url, json=body1, headers=headers)
    print(f"DEBUG: Response status: {response1.status_code}")
    print(f"DEBUG: Response content: {response1.text[:500]}...")  # Truncate log for readability

    route_data1 = response1.json()

    # If ORS returned an error payload, forward a helpful message
    if 'error' in route_data1:
        return JsonResponse({
            'error': 'Route calculation failed',
            'api_error': route_data1.get('error', 'Unknown error'),
            'message': route_data1.get('message', ''),
            'status': route_data1.get('status', {})
        }, status=400)

    if 'routes' not in route_data1 or not route_data1['routes']:
        return JsonResponse({
            'error': 'Invalid route response from API',
            'response': route_data1
        }, status=500)

    # Parse the first route result (distance in meters, duration in seconds)
    try:
        route = route_data1['routes'][0]
        coords1 = decode_geometry(route['geometry'])  # decode encoded polyline -> list of [lon, lat]
        distance1_m = route['summary']['distance']
        duration1_s = route['summary']['duration']
    except (KeyError, IndexError) as e:
        return JsonResponse({
            'error': 'Failed to parse route data',
            'response': route_data1,
            'exception': str(e)
        }, status=500)

    # ============================================================
    # 2) Request route: pickup -> dropoff
    # ============================================================
    body2 = {
        'coordinates': [[pickup_coords[1], pickup_coords[0]], [dropoff_coords[1], dropoff_coords[0]]]
    }

    print("DEBUG: Making API call for pickup -> dropoff")
    response2 = requests.post(url, json=body2, headers=headers)
    print(f"DEBUG: Response status: {response2.status_code}")

    route_data2 = response2.json()

    if 'error' in route_data2:
        return JsonResponse({
            'error': 'Second route calculation failed',
            'api_error': route_data2.get('error', 'Unknown error')
        }, status=400)

    if 'routes' not in route_data2 or not route_data2['routes']:
        return JsonResponse({'error': 'Invalid second route response'}, status=500)

    try:
        route = route_data2['routes'][0]
        coords2 = decode_geometry(route['geometry'])
        distance2_m = route['summary']['distance']
        duration2_s = route['summary']['duration']
    except (KeyError, IndexError) as e:
        return JsonResponse({'error': 'Failed to parse second route data', 'exception': str(e)}, status=500)

    # ------------------------------------------------------------
    # Convert units for easier reasoning downstream:
    # meters -> miles, seconds -> hours
    # ------------------------------------------------------------
    distance1_mi = distance1_m / 1609.34
    duration1_hr = duration1_s / 3600
    distance2_mi = distance2_m / 1609.34
    duration2_hr = duration2_s / 3600

    # Build full coordinate list for the entire trip (concatenate routes)
    full_coords = coords1 + coords2[1:]  # avoid duplicating the pickup point
    total_mi = distance1_mi + distance2_mi
    total_hr = duration1_hr + duration2_hr
    avg_mph = total_mi / total_hr if total_hr > 0 else 0

    print(f"DEBUG: Total distance: {total_mi:.1f} miles, duration: {total_hr:.1f} hours")

    # ------------------------------------------------------------
    # Helper: get_cum_mi(coords)
    # Computes cumulative miles along polyline points for stop placement.
    # Input `coords` expected as list of [lon, lat].
    # ------------------------------------------------------------
    def get_cum_mi(coords):
        lat_lon = [[lat, lon] for lon, lat in coords]
        cum = [0.0]
        for i in range(1, len(lat_lon)):
            d = geo_distance(lat_lon[i-1], lat_lon[i]).miles
            cum.append(cum[-1] + d)
        return cum

    full_cum = get_cum_mi([[lon, lat] for lon, lat in full_coords])

    # ============================================================
    # Compute stops:
    #  - Fueling every 1000 miles (interpolate along route)
    #  - Add pickup and dropoff explicitly
    # ============================================================
    stops = []
    next_fuel = 1000
    while next_fuel < total_mi:
        for i in range(1, len(full_cum)):
            if full_cum[i] >= next_fuel >= full_cum[i-1]:
                # Linear interpolation between full_coords[i-1] and full_coords[i]
                frac = (next_fuel - full_cum[i-1]) / (full_cum[i] - full_cum[i-1])
                lon = full_coords[i-1][0] + frac * (full_coords[i][0] - full_coords[i-1][0])
                lat = full_coords[i-1][1] + frac * (full_coords[i][1] - full_coords[i-1][1])
                stops.append({'lat': lat, 'lon': lon, 'type': f'Fueling at {next_fuel} mi'})
                break
        next_fuel += 1000

    # Always include pickup & dropoff
    stops.append({'lat': pickup_coords[0], 'lon': pickup_coords[1], 'type': 'Pickup'})
    stops.append({'lat': dropoff_coords[0], 'lon': dropoff_coords[1], 'type': 'Dropoff'})

    # ============================================================
    # Simulate Hours of Service (HOS) events and generate timeline
    # - Uses simplified HOS rules:
    #   - 11 hours driving / 14-hour window / 70 hours in 8 days
    #   - 30 minute break after 8 driving hours
    #   - Fueling and pickups cause time increments
    # ============================================================
    start_time = datetime(2025, 10, 15, 18, 45)  # baseline start time (example)
    current_time = start_time
    current_mi = 0.0
    i = 0  # index for cumulative mile lookup
    window_start = start_time
    last_break_end = start_time
    cum_drive_day = 0.0
    cum_on_day = 0.0
    cum_on_8day = cycle_hours  # initialize with provided hours used in current cycle
    next_fuel = 1000.0
    is_to_pickup = True
    segment_mi = distance1_mi
    events = []
    current_status = 3  # 3 == On Duty (driving start), mapping is used in log generation
    current_lat, current_lon = current_coords[0], current_coords[1]

    # add_event: small helper to append an event to events[] with computed day/hours
    add_event = lambda status, loc: events.append({
        'day': current_time.date(),
        'hours': (current_time - current_time.replace(hour=0, minute=0, second=0)).total_seconds() / 3600,
        'status': status,
        'location': loc
    })

    # initial log entry: start of trip
    add_event(3, f'Start at {current_location}')

    # -------------------------
    # Main simulation loop
    # -------------------------
    while current_mi < total_mi:
        # time since the current 14-hour window start
        time_since_window = (current_time - window_start).total_seconds() / 3600

        # -------- enforce long rest (10h or 34h) --------
        # If driver exceeded daily drive limit, window or 8-day cycle, schedule rest.
        if cum_drive_day >= 11 or time_since_window >= 14 or cum_on_8day >= 70:
            # Choose 10h rest unless 8-day limit exceeded then 34h reset
            rest_hours = 10 if cum_on_8day < 70 else 34
            add_event(0, f'Rest Stop ({rest_hours}hrs)')
            current_time += timedelta(hours=rest_hours)
            add_event(3, 'End Rest')
            # reset window counters appropriately
            window_start = current_time
            last_break_end = current_time
            cum_drive_day = 0
            cum_on_day = 0
            # If a 34h reset occurred, reduce 8-day accumulation accordingly
            cum_on_8day = max(0, cum_on_8day - (rest_hours if rest_hours == 34 else 0))
            stops.append({'lat': current_lat, 'lon': current_lon, 'type': 'Rest Stop'})

        # -------- enforce 30-minute break after ~8 hours driving --------
        drive_since_break = cum_drive_day - (last_break_end - window_start).total_seconds() / 3600 if last_break_end > window_start else cum_drive_day
        if drive_since_break >= 8:
            add_event(0, '30min Break')
            current_time += timedelta(minutes=30)
            add_event(2, 'End Break')
            last_break_end = current_time
            drive_since_break = 0
            stops.append({'lat': current_lat, 'lon': current_lon, 'type': 'Break'})

        # -------- at pickup point: add 1 hour dwell time and switch segment --------
        if is_to_pickup and current_mi >= distance1_mi:
            add_event(3, f'Pickup at {pickup_location}')
            current_time += timedelta(hours=1)  # 1 hour for pickup
            cum_on_day += 1
            cum_on_8day += 1
            add_event(2, 'Start to Dropoff')
            is_to_pickup = False
            segment_mi = distance2_mi

        # -------- compute the maximum allowed drive for the next step --------
        max_drive_break = 8 - drive_since_break if drive_since_break < 8 else 0
        max_drive_day = 11 - cum_drive_day
        max_drive_window = 14 - time_since_window
        # max_drive is in miles: use avg_mph and remaining trip to cap
        max_drive = min(max_drive_break, max_drive_day, max_drive_window, (total_mi - current_mi) / avg_mph) * avg_mph

        # -------- cap driving so that fueling is respected --------
        if current_mi + max_drive > next_fuel:
            max_drive = (next_fuel - current_mi)

        # -------- perform a driving block if any driving is allowed --------
        if max_drive > 0:
            add_event(2, 'Driving')
            current_time += timedelta(hours=max_drive / avg_mph)
            current_mi += max_drive
            cum_drive_day += max_drive / avg_mph
            cum_on_day += max_drive / avg_mph
            cum_on_8day += max_drive / avg_mph
            drive_since_break += max_drive / avg_mph

            # -------- translate current_mi into an interpolated lat/lon --------
            target = current_mi
            while i < len(full_cum) - 1 and full_cum[i+1] < target:
                i += 1
            if i < len(full_cum) - 1:
                # fractional position between two polyline points
                frac = (target - full_cum[i]) / (full_cum[i+1] - full_cum[i])
                current_lat = full_coords[i][1] + frac * (full_coords[i+1][1] - full_coords[i][1])
                current_lon = full_coords[i][0] + frac * (full_coords[i+1][0] - full_coords[i][0])
            else:
                # reached or exceeded end of route
                current_lat, current_lon = full_coords[-1][1], full_coords[-1][0]

            # -------- fueling events (30 minutes) --------
            if current_mi >= next_fuel:
                add_event(3, 'Fueling')
                current_time += timedelta(minutes=30)
                cum_on_day += 0.5
                cum_on_8day += 0.5
                add_event(2, 'End Fueling')
                next_fuel += 1000
                stops.append({'lat': current_lat, 'lon': current_lon, 'type': 'Fueling'})

        # -------- finish trip when we've arrived at total_mi --------
        if current_mi >= total_mi:
            add_event(3, f'Dropoff at {dropoff_location}')
            current_time += timedelta(hours=1)  # 1 hour dwell time for dropoff
            cum_on_day += 1
            cum_on_8day += 1
            add_event(0, 'Off Duty')

    # ============================================================
    # Build ELD daily log images from events
    # - Group events by day, ensure a leading 0-hour off-duty marker,
    # - Render a PNG for each day and return as base64 data URLs.
    # ============================================================
    day_events = defaultdict(list)
    for e in events:
        day_events[e['day']].append(e)

    eld_logs = []
    for day, day_ev in day_events.items():
        # Ensure day starts at 0 hours with Off Duty if needed
        if day_ev[0]['hours'] > 0:
            day_ev.insert(0, {'hours': 0, 'status': 0, 'location': ''})
        img = generate_log_image(day, day_ev)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        image_url = f'data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}'
        eld_logs.append({'day': day.strftime('%Y-%m-%d'), 'image_url': image_url})

    # ============================================================
    # Final JSON response
    # route.coordinates: list of [lon, lat] points for frontend mapping
    # stops: array of marker objects (fueling/pickup/dropoff/rest)
    # eld_logs: list of {day, image_url} data URLs
    # ============================================================
    return JsonResponse({
        'route': {'coordinates': full_coords, 'stops': stops, 'distance': total_mi, 'duration': total_hr},
        'eld_logs': eld_logs
    })


# ===============================================================
# HELPER: decode_geometry
# ---------------------------------------------------------------
# Decodes OpenRouteService encoded polyline geometry into a list of
# [lon, lat] coordinates. This follows the standard encoded polyline
# algorithm used by ORS.
# ===============================================================
def decode_geometry(encoded):
    coordinates = []
    index = 0
    lat = 0
    lon = 0

    while index < len(encoded):
        shift = 0
        result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        lat_change = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += lat_change

        shift = 0
        result = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        lon_change = ~(result >> 1) if (result & 1) else (result >> 1)
        lon += lon_change

        coordinates.append([lon * 1e-5, lat * 1e-5])

    return coordinates


# ===============================================================
# HELPER: generate_log_image
# ---------------------------------------------------------------
# Renders an ELD-style daily grid and draws the driver status line
# based on events for that day. Returns a PIL Image object.
# ===============================================================
def generate_log_image(day, events):
    img = Image.new('RGB', (1200, 600), 'white')
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Header text
    draw.text((50, 20), "Driver's Daily Log", font=font, fill='black')
    draw.text((50, 40), f"Date: {day.strftime('%m/%d/%Y')}", font=font, fill='black')

    # Grid layout constants
    grid_top = 100
    row_h = 50
    grid_bottom = grid_top + 4 * row_h  # bottom of the 4-row status grid
    labels = ['Off Duty', 'Sleeper Berth', 'Driving', 'On Duty (Not Driving)']

    # Draw horizontal rows and row labels
    for r in range(5):
        y = grid_top + r * row_h
        draw.line((50, y, 1150, y), fill='black')
    for r in range(4):
        draw.text((10, grid_top + r * row_h + 10), labels[r], font=font, fill='black')

    # Vertical hour grid (24 hours)
    hour_w = 1100 / 24
    for h in range(25):
        x = 50 + h * hour_w
        draw.line((x, grid_top, x, grid_bottom), fill='black')

    # Minor tick marks for quarter-hours
    for h in range(24):
        for q in range(1, 4):
            x = 50 + h * hour_w + q * (hour_w / 4)
            draw.line((x, grid_top, x, grid_top + 5), fill='black')
            draw.line((x, grid_bottom, x, grid_bottom - 5), fill='black')

    # Hour labels (Mid, 1, 2, ..., Noon, ...)
    for h in range(25):
        x = 50 + (h - 0.5) * hour_w if h > 0 else 50
        label = 'Mid' if h == 0 else 'Noon' if h == 12 else str(h % 12) if h != 12 else '12'
        draw.text((x - 10, grid_top - 20), label, font=font, fill='black')

    # Draw the status polyline (Off/Duty/Sleeping/Driving)
    line_w = 3
    prev_hours = 0
    prev_status = events[0]['status']
    prev_x = 50
    for e in events[1:]:
        # Map event hour -> x coordinate
        x = 50 + e['hours'] * hour_w
        # y coordinate for previous status row center
        y = grid_top + prev_status * row_h + row_h / 2
        # horizontal segment at previous status level
        draw.line((prev_x, y, x, y), fill='black', width=line_w)
        # vertical transition to new status
        new_y = grid_top + e['status'] * row_h + row_h / 2
        draw.line((x, y, x, new_y), fill='black', width=line_w)
        # annotate location under the grid
        draw.text((x, grid_bottom + 10), e['location'], font=font, fill='black')
        prev_x = x
        prev_status = e['status']

    # Extend the final status line to the end of the grid
    x = 1150
    y = grid_top + prev_status * row_h + row_h / 2
    draw.line((prev_x, y, x, y), fill='black', width=line_w)

    return img
