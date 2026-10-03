# Nodes Application Documentation

## Purpose

This Django application manages organizational structure, physical locations, IT devices, peripherals, assignments, and material handover reports.

The Django app package and label are both `nodes`. The Django project configuration is in `core`.

## In-App Documentation

The shared help content is maintained in `nodes/templates/inventory/docs.html` as the **Nodes Management Documentation** modal. `base.html` includes this template on application pages, and the footer's **Docs** link opens it using the `#manualModal` Bootstrap modal target. It is not a separate routed page.

The modal summarizes the physical-location and organization hierarchies, device types, validation rules, assignment constraints, deletion behavior, and material handover workflow. Keep its descriptions aligned with the Django models, form validation, and foreign-key `on_delete` policies.

## Core Object Model

The application has four related domains:

1. Physical infrastructure
2. Organizational structure
3. Hardware and peripherals
4. User assignments and handover reports

### Physical infrastructure

```text
City
└── Area
    └── Building
        └── Floor
            ├── Room
            │   └── Space
            │       ├── Device
            │       └── Socket
            └── CommonArea
                ├── Device
                └── Socket
```

A `CommonArea` belongs directly to a `Floor`. A normal `Room` contains one or more `Space` records. Devices and sockets can be located either in a `Space` or in a `CommonArea`.

### Organizational structure

```text
GeneralDirectorate
└── Directorate
    └── Department
        └── Office
            └── User
```

The four organization fields on `User` are independent optional foreign keys. A user may have one value in any combination of these fields, including all four fields at the same time. Each field is a single foreign key, so a user can have no more than one value for each category.

Example:

```text
User
├── general_directorate = Public Health
├── directorate         = Administration
├── department          = Materials
└── office              = Athens Office
```

There is no rule requiring a user to belong to exactly one of the four fields.

## Model Relationships

### City and Area

- `Area.city` points to `City`.
- A city can contain many areas.
- Deleting a city is restricted while areas exist.
- Area names are unique within a city, case-insensitively.

### Area and Building

- `Building.area` points to `Area`.
- A building can contain many floors, rooms through floors, common areas, sockets, and devices.
- Deleting an area is restricted while buildings exist.
- Building names are unique within an area, case-insensitively.

### Building and Floor

- `Floor.building` points to `Building`.
- Floor numbers are unique within a building.
- Floor numbers cannot be lower than `-2`.
- Deleting a building is restricted while floors exist.

### Floor, Room, Space, and CommonArea

- `Room.floor` points to `Floor`.
- `Space.room` points to `Room`.
- `CommonArea.floor` points to `Floor`.
- Room codes are unique within a floor, case-insensitively.
- Space names are unique within a room, case-insensitively.
- Common area names are unique within a floor, case-insensitively.
- Rooms and spaces use cascade deletion from their parent.
- Common areas use cascade deletion from their floor.

### Socket

A socket has three location-related fields:

- `space`
- `common_area`
- `building`

Business validation requires exactly one of `space` or `common_area`:

- Both empty: invalid.
- Both populated: invalid.
- `building` is derived from the selected space or common area during save.
- Socket codes are normalized to uppercase.
- Socket codes are unique within a building, case-insensitively.
- A socket may be deleted without deleting a device connected to it because `Device.socket` uses `SET_NULL`.

### User organization

- `Directorate.general_directorate` uses `RESTRICT`.
- `Department.directorate` uses `CASCADE`.
- `Office.department` uses `CASCADE`.
- `User.general_directorate` uses `RESTRICT`.
- `User.directorate`, `User.department`, and `User.office` use `CASCADE`.

Because of these policies, deleting a directorate or lower-level organization can remove dependent records. Deleting a general directorate is blocked when restricted children still exist.

## Lifecycle Behavior

Most structural and hardware models inherit from `LifeCycle`:

- `is_active`: whether the record is currently active.
- `valid_from`: date from which the record is valid.
- `valid_to`: optional expiration date.

Rules:

- `valid_to` cannot be earlier than `valid_from`.
- Records whose `valid_from` is in the future are automatically saved inactive.
- Records whose `valid_to` is in the past are automatically saved inactive.
- Lifecycle dates do not delete records; they control active status.

`Assignment` does not inherit from `LifeCycle`. It uses `assignment_date` and optional `end_date` instead.

## Devices

`Device` is the shared parent model for hardware. Concrete hardware models use Django multi-table inheritance:

```text
Device
├── DesktopComputer
├── AllInOneComputer
├── LaptopComputer
├── ServerComputer
├── Printer
├── Ups
├── Switch
├── AccessPoint
└── Phone
```

The base `Device` stores shared values:

- Brand and model
- Serial number
- Registration code
- IP and MAC addresses
- Usage type
- Physical location
- Optional socket

Subclass tables store type-specific data, such as CPU/RAM for computers, capacity for UPS devices, or port information for switches.

### Device location rules

A device must belong to exactly one physical location type:

- `space`, or
- `common_area`

The following states are invalid:

- Neither location selected.
- Both locations selected.

The device socket is optional. If selected:

- A socket can be assigned to only one device.
- The socket and device must belong to the same building.
- Deleting the socket leaves the device in place and clears the socket reference.

Device serial numbers, registration codes, IP addresses, and MAC addresses are unique where provided by the model definition.

### Peripherals

A `Peripheral` belongs to one `Device` through `Peripheral.device`.

Examples include keyboards, monitors, and mice. Deleting a device cascades to its peripherals.

## Assignments

An `Assignment` connects one `User` to one `Device` for a time period.

Fields:

- User
- Device
- Assignment type: `primary`, `shared`, or `temporary`
- Assignment start date
- Optional end date
- Notes

Validation rules:

- An end date cannot be earlier than the assignment date.
- A device with an existing shared assignment cannot receive a non-shared assignment.
- A shared assignment cannot coexist with a primary assignment on the same device.
- Primary assignments for the same device cannot overlap in time.
- The same user cannot have overlapping primary assignments for the same device.
- A primary and temporary assignment cannot overlap for the same user and device.
- An open-ended assignment is treated as ending on `9999-12-31` for overlap checks.

Assignments are deleted when their user or device is deleted because both foreign keys use `CASCADE`.

## Material Handover Report

The handover workflow is exposed at `/material-handover/`.

1. Select one or more users.
2. Select up to five devices.
3. Enter the report date and comments.
4. Submit the form.
5. The application renders a printable report.
6. The report includes organization values, full names, phone/email, selected devices, serial numbers, and signature areas.

For multiple selected users:

- Different values are displayed comma-separated.
- If all selected users share one value, it is displayed once with `(common)`.
- Missing values display as `Unregistered`.

The printable report is implemented in `nodes/templates/inventory/material-handover-report.html`. Browser-generated print headers and footers, such as the date, URL, and page count, must be disabled in the browser print dialog.

## Deletion Semantics

The `on_delete` policy determines what happens when a referenced parent is deleted:

| Policy | Behavior in this application |
|---|---|
| `RESTRICT` | Blocks deletion while dependent records exist. Used for important hierarchy roots such as City, Area, Building, and some organization parents. |
| `CASCADE` | Deletes dependent records automatically. Used for lower-level location objects, organization children, peripherals, and assignments. |
| `SET_NULL` | Keeps the child and clears the relationship. Used for an optional device socket. |

Before deleting a record, check its detail page and dependent lists. Cascading deletion may remove more than one record.

## Safe Record Creation Order

Create records from the top of their hierarchy toward the dependent records. A child cannot be created correctly until its required parent exists.

### Physical records

1. Create a `City`.
2. Create an `Area` and select its city.
3. Create a `Building` and select its area.
4. Create a `Floor` and select its building.
5. Create either a `Room` on the floor and then a `Space` inside the room, or a `CommonArea` directly on the floor.
6. Create a `Socket` and select exactly one location: Space or Common Area. Its building is derived from that location.
7. Create a `Device` and select exactly one location: Space or Common Area.
8. Optionally connect the device to a socket in the same building.
9. Create any `Peripheral` and attach it to the device.

### Organization records

1. Create a `GeneralDirectorate`.
2. Create a `Directorate` and select its general directorate.
3. Create a `Department` and select its directorate.
4. Create an `Office` and select its department.
5. Create a `User` and select any applicable organization fields. Each field is optional, but each selected field accepts only one related object.

### Assignments

Create users and devices before creating an `Assignment`:

1. Select an existing user.
2. Select an existing device.
3. Set the assignment type and start date.
4. Set an end date only when the assignment is temporary or closed.
5. Confirm that the date range does not overlap an existing incompatible assignment.

## Important Restrictions During Creation

- A floor number must be unique within its building and cannot be lower than `-2`.
- Room codes, spaces, common areas, buildings, areas, and socket codes must be unique within their parent scope.
- A socket must have exactly one location: Space or Common Area.
- A device must have exactly one location: Space or Common Area.
- A device socket must belong to the same building as the device.
- One socket cannot be assigned to multiple devices.
- A user may have one general directorate, one directorate, one department, and one office at the same time. The application does not require exactly one total organization field.
- A primary assignment cannot overlap another primary assignment for the same device.
- Shared assignments cannot coexist with a primary assignment on the same device.
- Primary and temporary assignments cannot overlap for the same user and device.
- An assignment end date cannot be earlier than its start date.

## Material Handover Creation Order

The handover report is created after the related users and devices already exist:

1. Create the organizational records and users.
2. Create the physical hierarchy and devices.
3. Optionally create assignments connecting users to devices.
4. Open the Material Handover form.
5. Select one or more users.
6. Select up to five devices.
7. Enter the report date and optional comments.
8. Submit the form and review the printable receipt report.

The report does not create users, devices, or assignments. It only reads the selected records and produces a printable document.

## Naming and Uniqueness

Most hierarchy names are normalized before saving:

- Leading and trailing whitespace is removed.
- Text is converted to lowercase and then capitalized.
- Case-insensitive uniqueness is enforced within the relevant parent.

Important uniqueness scopes:

- City name: globally unique, case-insensitive.
- Area name: unique within a city.
- Building name: unique within an area.
- Floor number: unique within a building.
- Room code: unique within a floor.
- Space name: unique within a room.
- Common area name: unique within a floor.
- Socket code: unique within a building.

## Main Routes

- `/`: dashboard
- `/cities/`, `/areas/`, `/buildings/`, `/floors/`
- `/rooms/`, `/spaces/`, `/common-areas/`, `/sockets/`
- `/general-directorates/`, `/directorates/`, `/departments/`, `/offices/`, `/users/`
- `/devices/` and type-specific hardware routes
- `/assignments/`
- `/material-handover/`

Each main entity generally has list, detail, create, update, and delete routes.

## Development Commands

Run commands from the directory containing `manage.py`:

```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py runserver
```

The current project has been verified with Django system checks and the application test suite.
