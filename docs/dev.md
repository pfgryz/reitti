# Development Documentation

### GraphHopper

Example API request to get route between stops `Liisankatu` and `Urho Kekkosen Katu` using `foot` profile and `mapnik` layer:
```sh
curl "http://localhost:8989/route?point=60.174230,24.956804&point=60.168345,24.931822&profile=foot&layer=mapnik"
```

Response looks like this:
```json
{
    "paths": [
        {
            "distance": 1701.96,
            "weight": 1033.972015,
            "time": 1237248,
        }
    ]
}
```

Distance is in meters, weight is in seconds, time is in milliseconds.

There is also an interactive map available at `http://localhost:8989/maps`.