# Base Station App

A Farm-ng dashboard application for managing GNSS base stations implemented at the Farm-ng's Brain.

> [!IMPORTANT]
> The `gnss-trip` server runs on a special flavor of the Amiga Brain. If you want to convert the
> Brain to a GNSS Ntrip Server (a.k.a. Base Station) contact our support team at suppor@farm-ng.com


## Features

- **Mode Management**: Switch between Fixed and Survey-in modes
- **Location Management**:
  - Save current surveyed positions as named locations
  - Select from previously saved locations
  - Delete stored locations
  - View location coordinates with cm-level precision
- **Real-time Monitoring**:
  - Current position display
  - Survey-in progress tracking
  - RTCM message monitoring

## Installation

From within the Brain configured to Base Station mode:

1. Clone the repository:
```bash
git clone https://github.com/farm-ng/base-station-app.git
cd base-station-app
```

2. Install the app:
```bash
./install.sh
```

3. Reboot the Brain and the App should apper on your main screen.

Alternativelly, you can run the app from the command line:
```bash
./entry.sh
```

Wait a few seconds and the app will appear in the Brain screen.

## Configuration

The app is a grpahical interface for two main configuration files:

- `/mnt/service_config/basestation.json`: GNSS base station configuration
- `src/utils/known-locations.json`: Saved location database

### Base Station Configuration Format (`/mnt/service_config/basestation.json`)
```json
{
    "USE_FIXED_MODE": true,
    "COORDINATES": {
        "LATITUDE": 37.12345678,
        "LONGITUDE": -121.12345678,
        "ALTITUDE": 123.45
    }
}
```

### Known Locations Format (`/mnt/managed-home/farm-ng-user-<YOUR-USERNAME>/base-station-app/src/utils/known-locations.json`)
```json
{
    "locations": [
        {
            "name": "Location 1 Name",
            "latitude": 37.12345678,
            "longitude": -121.12345678,
            "altitude": 123.45
        },
        {
            "name": "Location 2 Name",
            "latitude": -37.12345678,
            "longitude": 121.12345678,
            "altitude": 67.89
        }
    ]
}
```

You can change both files manually using t he CLI as well. Use the services tab to re-start
`farmng-gnss-ntrip.service` to apply the changes.

## Usage

The Survey-in mode uses obaservations of a few minutes to lock-in the position of the base station.
If you are using the base station on a location that it have never been used before, start at this
mode.

To minimize normal GPS location fluctuation, once a position is stablished, you can lock the
coordinates using fixed mode. Every time you place the location on the same physical location,
you can retrieve the lat, lon, height position and make sure your paths are repeatable.

Here's how a typical workflow look like:

1. Launch the app from the Farm-ng dashboard
2. Choose operating mode:
   - **Survey-in Mode**: For determining new base station positions
   - **Fixed Mode**: For operating with known coordinates
3. Save locations:
   - Wait 30 minutes for survey-in to complete
   - Click "Save Location" and enter a name
4. Select saved locations:
   - Switch to Fixed mode
   - Click "Select Location"
   - Choose from the list

## Support
If you have quesitons, concerns, or suggestions for this or any of Farm-ng repos,
email support@farm-ng.com
