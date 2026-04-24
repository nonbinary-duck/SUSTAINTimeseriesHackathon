import requests
from bs4 import BeautifulSoup
import pandas as pd
import io
import time

# I've embedded the full HTML table here to ensure the script works immediately
HTML_INPUT = """
<table class="table alternate-bg">
<thead>
<tr>
<th scope="col">Name</th>
<th scope="col">Location</th>
<th scope="col">Opened</th>
<th scope="col">Data</th>
</tr>
</thead>
<tbody>
<tr><td>Aberporth</td><td>-4.57, 52.139</td><td>1941</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/aberporthdata.txt">View data</a></td></tr>
<tr><td>Armagh</td><td>-6.649, 54.352</td><td>1853</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/armaghdata.txt">View data</a></td></tr>
<tr><td>Ballypatrick Forest</td><td>-6.153, 55.181</td><td>1961</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/ballypatrickdata.txt">View data</a></td></tr>
<tr><td>Bradford</td><td>-1.772, 53.813</td><td>1908</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/bradforddata.txt">View data</a></td></tr>
<tr><td>Braemar No 2</td><td>-3.396, 57.011</td><td>1959</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/braemardata.txt">View data</a></td></tr>
<tr><td>Camborne</td><td>-5.327, 50.218</td><td>1978</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/cambornedata.txt">View data</a></td></tr>
<tr><td>Cambridge Niab</td><td>0.102, 52.245</td><td>1959</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/cambridgedata.txt">View data</a></td></tr>
<tr><td>Cardiff Bute Park</td><td>-3.187, 51.488</td><td>1977</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/cardiffdata.txt">View data</a></td></tr>
<tr><td>Chivenor</td><td>-4.147, 51.089</td><td>1951</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/chivenordata.txt">View data</a></td></tr>
<tr><td>Cwmystwyth</td><td>-3.802, 52.358</td><td>1959</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/cwmystwythdata.txt">View data</a></td></tr>
<tr><td>Dunstaffnage</td><td>-5.439, 56.451</td><td>1971</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/dunstaffnagedata.txt">View data</a></td></tr>
<tr><td>Durham</td><td>-1.585, 54.768</td><td>1880</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/durhamdata.txt">View data</a></td></tr>
<tr><td>Eastbourne</td><td>0.285, 50.759</td><td>1959</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/eastbournedata.txt">View data</a></td></tr>
<tr><td>Eskdalemuir</td><td>-3.205, 55.312</td><td>1911</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/eskdalemuirdata.txt">View data</a></td></tr>
<tr><td>Heathrow</td><td>-0.452, 51.479</td><td>1948</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/heathrowdata.txt">View data</a></td></tr>
<tr><td>Hurn</td><td>-1.835, 50.779</td><td>1957</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/hurndata.txt">View data</a></td></tr>
<tr><td>Lerwick</td><td>-1.183, 60.139</td><td>1931</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/lerwickdata.txt">View data</a></td></tr>
<tr><td>Leuchars</td><td>-2.861, 56.377</td><td>1957</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/leucharsdata.txt">View data</a></td></tr>
<tr><td>Lowestoft Monckton Avenue</td><td>1.727, 52.483</td><td>1914</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/lowestoftdata.txt">View data</a></td></tr>
<tr><td>Manston</td><td>1.337, 51.346</td><td>1934</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/manstondata.txt">View data</a></td></tr>
<tr><td>Nairn Druim</td><td>-3.821, 57.593</td><td>1931</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/nairndata.txt">View data</a></td></tr>
<tr><td>Newton Rigg</td><td>-2.786, 54.67</td><td>1959</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/newtonriggdata.txt">View data</a></td></tr>
<tr><td>Oxford</td><td>-1.262, 51.761</td><td>1853</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/oxforddata.txt">View data</a></td></tr>
<tr><td>Paisley</td><td>-4.43, 55.846</td><td>1959</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/paisleydata.txt">View data</a></td></tr>
<tr><td>Ringway</td><td>-2.279, 53.356</td><td>1946</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/ringwaydata.txt">View data</a></td></tr>
<tr><td>Ross-on-wye</td><td>-2.584, 51.911</td><td>1931</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/rossonwyedata.txt">View data</a></td></tr>
<tr><td>Shawbury</td><td>-2.663, 52.794</td><td>1946</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/shawburydata.txt">View data</a></td></tr>
<tr><td>Sheffield</td><td>-1.49, 53.381</td><td>1883</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/sheffielddata.txt">View data</a></td></tr>
<tr><td>Southampton Mayflower Park</td><td>-1.408, 50.898</td><td>1855</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/southamptondata.txt">View data</a></td></tr>
<tr><td>Stornoway Airport</td><td>-6.318, 58.214</td><td>1873</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/stornowaydata.txt">View data</a></td></tr>
<tr><td>Sutton Bonington</td><td>-1.25, 52.836</td><td>1959</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/suttonboningtondata.txt">View data</a></td></tr>
<tr><td>Tiree</td><td>-6.88, 56.5</td><td>1928</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/tireedata.txt">View data</a></td></tr>
<tr><td>Valley</td><td>-4.535, 53.252</td><td>1931</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/valleydata.txt">View data</a></td></tr>
<tr><td>Waddington</td><td>-0.522, 53.175</td><td>1947</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/waddingtondata.txt">View data</a></td></tr>
<tr><td>Whitby</td><td>-0.624, 54.481</td><td>1961</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/whitbydata.txt">View data</a></td></tr>
<tr><td>Wick Airport</td><td>-3.088, 58.454</td><td>1914</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/wickairportdata.txt">View data</a></td></tr>
<tr><td>Yeovilton</td><td>-2.641, 51.006</td><td>1964</td><td><a href="https://www.metoffice.gov.uk/pub/data/weather/uk/climate/stationdata/yeoviltondata.txt">View data</a></td></tr>
</tbody>
</table>
"""

def get_station_list(html):
    soup = BeautifulSoup(html, 'html.parser')
    stations = []
    
    # More robust searching: find table, then find all tr
    table = soup.find('table')
    if not table:
        print("Could not find table in HTML.")
        return []
        
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if not cols: continue # Skip header rows
        
        name = cols[0].get_text(strip=True)
        
        # Requirement: Discard Lerwick
        if name.lower() == 'lerwick':
            continue
            
        location_raw = cols[1].get_text(strip=True).split(',')
        if len(location_raw) < 2: continue
        
        lon = location_raw[0].strip()
        lat = location_raw[1].strip()
        
        link = cols[3].find('a')
        if not link: continue
        url = link['href']
        
        stations.append({
            'name': name,
            'lat': lat,
            'lon': lon,
            'url': url
        })
    return stations

def process_station_data(station):
    print(f"Fetching: {station['name']}...", end=" ", flush=True)
    try:
        # Met Office site sometimes blocks fast requests, so we use a header
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(station['url'], headers=headers, timeout=10)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        
        # Find where the actual data table starts
        start_row = 0
        for i, line in enumerate(lines):
            if "yyyy" in line:
                start_row = i + 2
                break
        
        data_rows = []
        for line in lines[start_row:]:
            # Skip empty lines
            if not line.strip(): continue
            
            # Clean symbols from Met Office data
            clean_line = line.replace('*', '').replace('#', '').replace('---', 'NaN')
            parts = clean_line.split()
            
            # We expect 7 columns: yyyy, mm, tmax, tmin, af, rain, sun
            # Some files might be missing 'sun' at the very end
            if len(parts) >= 6:
                row = {
                    'station_name': station['name'],
                    'lat': station['lat'],
                    'lon': station['lon'],
                    'year': parts[0],
                    'month': parts[1],
                    'tmax_degC': parts[2],
                    'tmin_degC': parts[3],
                    'af_days': parts[4],
                    'rain_mm': parts[5],
                    'sun_hours': parts[6] if len(parts) > 6 else 'NaN'
                }
                data_rows.append(row)
        
        print(f"Done ({len(data_rows)} months)")
        return data_rows
    except Exception as e:
        print(f"Failed: {e}")
        return []

def main():
    stations = get_station_list(HTML_INPUT)
    print(f"Found {len(stations)} stations (Lerwick excluded). Starting downloads...\n")
    
    all_records = []
    for station in stations:
        data = process_station_data(station)
        all_records.extend(data)
        # Polite delay to avoid getting IP blocked
        time.sleep(0.5)
        
    if not all_records:
        print("No data was collected.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(all_records)
    
    # Numeric conversion
    cols_to_fix = ['lat', 'lon', 'year', 'month', 'tmax_degC', 'tmin_degC', 'af_days', 'rain_mm', 'sun_hours']
    for col in cols_to_fix:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    output_filename = "met_office_all_stations.csv"
    df.to_csv(output_filename, index=False)
    print(f"\nSaved {len(df)} rows to {output_filename}")

if __name__ == "__main__":
    main()