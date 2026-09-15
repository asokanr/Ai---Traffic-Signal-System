# Smart Traffic AI Project - Entity-Relationship (ER) Diagram

This document contains the Entity-Relationship (ER) diagram reflecting the actual Django models from the `traffic_signal_project` (including User Account configuration, Junctions, Signals, and Logs).

## ER Diagram (Mermaid)

```mermaid
erDiagram
    user {
        int id PK
        string username
        string email
        string password
        boolean is_active
        boolean is_staff
        datetime date_joined
    }

    user_profile {
        int id PK
        int user_id FK
        string role
        string phone
        datetime created_at
    }

    otp {
        int id PK
        int user_id FK
        string otp
        boolean is_verified
    }

    junction {
        int id PK
        string name
        string code
        float latitude
        float longitude
        boolean is_active
        datetime created_at
    }

    traffic_signal {
        int id PK
        int junction_id FK
        string direction
        string current_state
        string mode
        boolean is_emergency_active
        int vehicle_count
        float current_weighted_density
        int green_time
        int yellow_time
        int red_time
        datetime last_updated
        datetime state_start_time
    }

    vehicle_type_config {
        int id PK
        string vehicle_type
        float weight
    }

    traffic_log {
        int id PK
        int signal_id FK
        int vehicle_count
        float weighted_density
        string signal_state
        int waiting_time
        boolean is_emergency
        datetime timestamp
    }

    vehicle_count {
        int id PK
        int signal_id FK
        int two_wheeler
        int four_wheeler
        int heavy_vehicle
        int emergency_vehicle
        int vehicles_passed
        int total_vehicles
        float weighted_score
        datetime timestamp
    }

    emergency_log {
        int id PK
        int signal_id FK
        datetime start_time
        datetime end_time
        boolean resolved
        float clearance_time
        string ambulance_id
        float ambulance_lat
        float ambulance_lng
    }

    signal_timing {
        int id PK
        int signal_id FK
        datetime green_start_time
        datetime green_end_time
        int total_green_time
        date date
    }

    admin_action_log {
        int id PK
        int user_id FK
        int junction_id FK
        int signal_id FK
        string action_type
        text description
        datetime timestamp
    }

    accident_alert {
        int id PK
        int junction_id FK
        string severity
        text description
        float latitude
        float longitude
        boolean is_active
        datetime reported_at
        datetime resolved_at
    }

    pollution_reading {
        int id PK
        int junction_id FK
        int aqi
        float pm25
        float pm10
        float co_level
        float no2_level
        datetime timestamp
    }

    %% Relationships
    user ||--|| user_profile : "has"
    user ||--|| otp : "secures via"
    user ||--o{ admin_action_log : "performs"

    junction ||--o{ traffic_signal : "contains"
    junction ||--o{ accident_alert : "reports"
    junction ||--o{ pollution_reading : "measures"
    junction ||--o{ admin_action_log : "target of"

    traffic_signal ||--o{ traffic_log : "generates"
    traffic_signal ||--o{ vehicle_count : "records"
    traffic_signal ||--o{ emergency_log : "experiences"
    traffic_signal ||--o{ signal_timing : "times"
    traffic_signal ||--o{ admin_action_log : "target of"
```

## Entity Descriptions

- **user**: Built-in Django authentication entity representing project users (Admins & Operators).
- **user_profile**: Extends the user model to specify Roles ("operator", "admin") and contact numbers.
- **otp**: Extension mapping generated OTPs for secure login verification.
- **junction**: Represents a physical traffic intersection running the Smart Traffic AI.
- **traffic_signal**: Each junction has multiple signals (Directions) capturing current states, modes (ADAPTIVE, EMERGENCY), and waiting densities.
- **vehicle_type_config**: Configures the dynamic density weighting given to bikes vs. cars vs. heavy vehicles.
- **traffic_log**: Stores historical logs of density changes at given signals.
- **vehicle_count**: Type-wise logs that capture details down to individual counts of 2-wheelers vs. 4-wheelers.
- **emergency_log**: Active and Historical sessions of Ambulance detection, linking GPS coordinates and duration.
- **signal_timing**: Collects Green Light time distribution per signal for analytics purposes.
- **admin_action_log**: System log table recording when admins force manual overrides on signals or junctions.
- **accident_alert**: Events representing flagged roadside anomalies or collisions detected at a specific junction.
- **pollution_reading**: Tracks air-quality logs gathered at the junction level based on emissions.
