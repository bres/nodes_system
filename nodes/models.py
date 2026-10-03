from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower
from django.utils import timezone
from datetime import date
from django.db.models import Value
from django.db.models.functions import Coalesce


# =====================================================
# BASE ABSTRACT MODEL
# =====================================================
# LifeCycle is not a real database table — it is abstract.
# Any model that extends it automatically gets these three fields.
# This lets you track whether a record is active, when it started,
# and when it ended — without repeating the same fields everywhere.
class LifeCycle(models.Model):
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(default=timezone.localdate)
    valid_to = models.DateField(null=True, blank=True)

    def clean(self):
        # Prevent impossible date ranges
        if self.valid_to and self.valid_from and self.valid_to < self.valid_from:
            raise ValidationError({
                "valid_to": "valid_to cannot be earlier than valid_from."
            })

    def save(self, *args, **kwargs):
        today = timezone.now().date()

        # Auto-deactivate if expired
        if self.valid_to and self.valid_to < today:
            self.is_active = False

        # Auto-deactivate if not yet valid
        if self.valid_from and self.valid_from > today:
            self.is_active = False

        super().save(*args, **kwargs)

    class Meta:
        abstract = True
       


# =====================================================
# GEOGRAPHICAL STRUCTURE
# =====================================================
# The physical location hierarchy is:
#   City → Area → Building → Floor → Room → Space
#                                  └──────→ CommonArea
#
# Example: Athens → Kolonaki → Main HQ → Floor 3 → Room 301 → Desk Area A
# CommonArea sits directly on a Floor (corridors, lobbies, server rooms).
class City(models.Model):
    name = models.CharField(max_length=150)

    class Meta:
        verbose_name = "city"
        verbose_name_plural = "cities"
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="city_name_ci_unique"
            )
        ]
        ordering = ["name"]

    def clean(self):
        if self.name:
            normalized = self.name.strip().lower().capitalize()
            if City.objects.filter(name__iexact=normalized).exclude(pk=self.pk).exists():
                raise ValidationError({"name": "This city already exists in the system."})
            self.name = normalized

    def save(self, *args, **kwargs):
        self.name = self.name.strip().lower().capitalize()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or ""


class Area(models.Model):
    city = models.ForeignKey(
        City,
        on_delete=models.RESTRICT,
        related_name="areas"
    )
    name = models.CharField(max_length=150)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "city",
                name="area_city_name_ci_unique"   # was: %(class)s_... only works in abstract models
            )
        ]
        ordering = ["name"]                        # was: missing entirely

    def clean(self):
        if self.name:
            normalized = self.name.strip().lower().capitalize()
        else:
            return

        if self.city_id and Area.objects.filter(   # was: self.city — triggers a DB hit to check truthiness
            city=self.city,
            name__iexact=normalized
        ).exclude(pk=self.pk).exists():
            raise ValidationError({"name": "This area already exists in this city."})

        self.name = normalized

    def save(self, *args, **kwargs):               # was: missing entirely
        if self.name:
            self.name = self.name.strip().lower().capitalize()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.city_id:
            return f"{self.city.name} - {self.name}"
        return self.name or ""
class Building(LifeCycle):
    area = models.ForeignKey(
        Area,
        on_delete=models.RESTRICT,
        related_name="buildings"
    )
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=250, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "area",
                name="building_name_ci_unique_per_area"
            )
        ]
        ordering = ["name"]

    def clean(self):
        if self.name:
            normalized = self.name.strip().lower().capitalize()
        else:
            return

        if self.area_id and Building.objects.filter(  # was: self.area — unnecessary DB hit
            area=self.area,
            name__iexact=normalized
        ).exclude(pk=self.pk).exists():
            raise ValidationError({
                "name": "This building already exists in this area."
            })

        self.name = normalized

        super().clean()  # was: missing — LifeCycle.clean() validates valid_from/valid_to

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().lower().capitalize()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.area_id:
            return f"{self.area.city.name} / {self.area.name} / {self.name}"
        return self.name or ""

class Floor(LifeCycle):
    building = models.ForeignKey(
        Building,
        on_delete=models.RESTRICT,
        related_name="floors"
    )
    floor_number = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["building", "floor_number"],
                name="unique_floor_number_per_building"
            ),
            models.CheckConstraint(
                condition=models.Q(floor_number__gte=-2),
                name="floor_number_min_minus_2",
                violation_error_message="The floor number cannot be less than -2."
            ),
        ]
        ordering = ["floor_number"]

    def clean(self):
        if self.floor_number is not None and self.floor_number < -2:
            raise ValidationError({
                "floor_number": "The floor number cannot be less than -2."
            })

        if self.building_id and self.floor_number is not None:
            if Floor.objects.filter(
                building=self.building,
                floor_number=self.floor_number
            ).exclude(pk=self.pk).exists():
                raise ValidationError({
                    "floor_number": "This floor already exists in this building."
                })

        super().clean()  # was: missing — skips LifeCycle date range validation



    def __str__(self):
            if self.building_id:
                return (
                    f"{self.building.area.city.name} / "
                    f"{self.building.area.name} / "
                    f"{self.building.name} / "
                    f"Floor {self.floor_number}"
                )
            return f"Floor {self.floor_number if self.floor_number is not None else '?'}"
   
    
# =====================================================
# COMMON AREA (Corridors, Lobbies, Server Rooms)
# =====================================================
# A CommonArea is a shared space on a Floor that is NOT a regular room.
# Devices and Sockets can be assigned directly to a CommonArea.
class CommonArea(LifeCycle):
    AREA_TYPE_CHOICES = [
        ("corridor",    "Corridor"),
        ("lobby",       "Lobby"),
        ("server_room", "Server Room"),
        ("other",       "Other"),
    ]

    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="common_areas"
    )
    name = models.CharField(max_length=150)
    area_type = models.CharField(max_length=20, choices=AREA_TYPE_CHOICES, default="corridor")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "floor",
                name="commonarea_name_ci_unique_per_floor"
            )
        ]
        ordering = ["name"]

    def clean(self):
        if self.name:
            normalized = self.name.strip().lower().capitalize()
        else:
            return

        if self.floor_id and CommonArea.objects.filter(
            floor=self.floor,
            name__iexact=normalized
        ).exclude(pk=self.pk).exists():
            raise ValidationError({"name": "This common area already exists on this floor."})

        self.name = normalized
        super().clean()

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().lower().capitalize()
        super().save(*args, **kwargs)

    @property
    def building(self):
        return self.floor.building

    def __str__(self):
        if self.floor_id:
            return (
                f"{self.floor.building.area.city.name} / "
                f"{self.floor.building.area.name} / "
                f"{self.floor.building.name} / "
                f"Floor {self.floor.floor_number} / "
                f"{self.name}"
            )
        return self.name or ""
    

# =====================================================
# ROOM
# =====================================================
# RoomManager auto-applies select_related so every Room query
# already has floor → building → area → city loaded in one SQL JOIN.
# This prevents N+1 queries when displaying rooms in lists or dropdowns.
class RoomManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related(
            "floor__building__area__city"
        )


class Room(LifeCycle):
    # A Room is a physical room on a Floor. It contains Spaces.
    floor = models.ForeignKey(
        Floor,
        on_delete=models.CASCADE,
        related_name="rooms"
    )
    room_code = models.CharField(max_length=50)

    # Use our custom manager as the default.
    objects = RoomManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("room_code"),
                "floor",
                name="room_code_ci_unique_per_floor"
            )
        ]

    # -----------------------------
    # VALIDATION (friendly errors)
    # -----------------------------
    def clean(self):
        # Normalize only if provided
        if self.room_code:
            normalized = self.room_code.strip().lower().capitalize()
        else:
            # Let Django show "This field is required."
            return

        # Duplicate check only if floor is selected
        if self.floor_id and Room.objects.filter(
            floor=self.floor,
            room_code__iexact=normalized
        ).exclude(pk=self.pk).exists():
            raise ValidationError({
                "room_code": "This room already exists on this floor."
            })

        # Assign normalized value so the form displays it
        self.room_code = normalized

    # -----------------------------
    # SAVE (DB‑safe normalization)
    # -----------------------------
    def save(self, *args, **kwargs):
        if self.room_code:
            self.room_code = self.room_code.strip().lower().capitalize()
        super().save(*args, **kwargs)

    # -----------------------------
    # SAFE __str__ (never crashes)
    # -----------------------------
    def __str__(self):
        if self.floor_id:
            return f"{self.floor} / {self.room_code}"
        return self.room_code or ""



# =====================================================
# SPACE
# =====================================================
# SpaceManager works the same as RoomManager — pre-loads the full
# location chain so Space queries never cause N+1 problems.
class SpaceManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related(
            "room__floor__building__area__city"
        )
class Space(LifeCycle):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="spaces")
    name = models.CharField(max_length=100)

    objects = SpaceManager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "room",
                name="unique_space_name_per_room_ci"
            )
        ]

    def clean(self):                                        # was: missing entirely
        if self.name:
            normalized = self.name.strip().capitalize()
        else:
            return

        if self.room_id and Space.objects.filter(
            room=self.room,
            name__iexact=normalized
        ).exclude(pk=self.pk).exists():
            raise ValidationError({"name": "This space already exists in this room."})

        self.name = normalized
        super().clean()                                     # was: missing — skips LifeCycle date validation

    def save(self, *args, **kwargs):
        if self.name:                                       # was: no guard, crashes if name is empty
            self.name = self.name.strip().capitalize()
        super().save(*args, **kwargs)

    @property
    def floor(self):
        return self.room.floor

    @property
    def device_count(self):
        return self.devices.count()

    @property
    def building(self):
        return self.room.floor.building

    def __str__(self):
        if self.room_id:
            return (
                f"{self.room.floor.building.area.city.name} / "
                f"{self.room.floor.building.area.name} / "
                f"{self.room.floor.building.name} / "
                f"Floor {self.room.floor.floor_number} / "
                f"{self.room.room_code} / "
                f"{self.name}"
            )
        return self.name or ""

# =====================================================
# SOCKET
# =====================================================
# A Socket is a physical network/power wall socket.
# It belongs to EITHER a Space OR a CommonArea — never both, never neither.
# Devices can optionally plug into a socket.
class Socket(LifeCycle):
    socket_code = models.CharField(
        max_length=50,
        help_text="Unique identifier for the socket."
    )

    # Exactly one of these two must be set
    space = models.ForeignKey(
        Space, null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="sockets"
    )
    common_area = models.ForeignKey(
        CommonArea, null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="sockets"
    )

    # Denormalized FK for uniqueness constraint
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="sockets"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("socket_code"),
                "building",
                name="socket_code_ci_unique_per_building"
            )
        ]
        ordering = ["socket_code"]

    def clean(self):
        # Normalize early
        if self.socket_code:
            self.socket_code = self.socket_code.strip().upper()

        # Location validation
        if bool(self.space) == bool(self.common_area):
            raise ValidationError("Select either a Space OR a Common Area.")

        # Determine building
        building = (
            self.space.room.floor.building
            if self.space
            else self.common_area.floor.building
        )

        # Duplicate check
        if Socket.objects.filter(
            building=building,
            socket_code__iexact=self.socket_code
        ).exclude(pk=self.pk).exists():
            raise ValidationError({
                "socket_code": "A socket with this code already exists in this building."
            })

    def save(self, *args, **kwargs):
        # Auto‑assign building AFTER clean() normalized the code
        if self.space:
            self.building = self.space.room.floor.building
        elif self.common_area:
            self.building = self.common_area.floor.building

        super().save(*args, **kwargs)

    @property
    def location(self):
        if self.space:
            return f"Space: {self.space}"
        if self.common_area:
            return f"Common Area: {self.common_area}"
        return "—"

    def __str__(self):
        return self.socket_code

# =====================================================
# ORGANIZATIONAL STRUCTURE
# =====================================================
# The org chart hierarchy is:
#   GeneralDirectorate → Directorate → Department → Office → User
#
# Example: Ministry of Finance → Budget Division → Tax Team → Athens Office → John Doe

class GeneralDirectorate(LifeCycle):
    name = models.CharField(max_length=200, unique=True)

    class Meta:
        ordering = ["name"]

    # -----------------------------
    # VALIDATION (friendly errors)
    # -----------------------------
    def clean(self):
        # Normalize only if provided
        if self.name:
            normalized = self.name.strip().lower().capitalize()
        else:
            return  # Let Django show "This field is required."

        # Duplicate check (case-insensitive)
        if GeneralDirectorate.objects.filter(
            name__iexact=normalized
        ).exclude(pk=self.pk).exists():
            raise ValidationError({
                "name": "This general directorate already exists."
            })

        # Assign normalized value so the form displays it
        self.name = normalized

    # -----------------------------
    # SAVE (DB‑safe normalization)
    # -----------------------------
    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().lower().capitalize()
        super().save(*args, **kwargs)

    # -----------------------------
    # SAFE __str__ (never crashes)
    # -----------------------------
    def __str__(self):
        return self.name or ""



class Directorate(LifeCycle):
    name = models.CharField(max_length=200)
    general_directorate = models.ForeignKey(
        GeneralDirectorate,
        on_delete=models.RESTRICT,
        related_name="directorates"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["general_directorate", "name"],
                name="unique_directorate_per_gd"
            )
        ]
        ordering = ["name"]

    # -----------------------------
    # VALIDATION (friendly errors)
    # -----------------------------
    def clean(self):
        # Normalize only if provided
        if self.name:
            normalized = self.name.strip().lower().capitalize()
        else:
            return  # Let Django show "This field is required."

        # Duplicate check only if GD is selected
        if self.general_directorate_id and Directorate.objects.filter(
            general_directorate=self.general_directorate,
            name__iexact=normalized
        ).exclude(pk=self.pk).exists():
            raise ValidationError({
                "name": "This directorate already exists under this general directorate."
            })

        # Assign normalized value so the form displays it
        self.name = normalized

    # -----------------------------
    # SAVE (DB‑safe normalization)
    # -----------------------------
    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().lower().capitalize()
        super().save(*args, **kwargs)

    # -----------------------------
    # SAFE __str__ (never crashes)
    # -----------------------------
    def __str__(self):
        return self.name or ""


class Department(LifeCycle):
    name = models.CharField(max_length=200)
    directorate = models.ForeignKey(
        Directorate,
        on_delete=models.CASCADE,
        related_name="departments"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["directorate", "name"],
                name="unique_department_per_directorate"
            )
        ]
        ordering = ["name"]

    # -----------------------------
    # VALIDATION (friendly errors)
    # -----------------------------
    def clean(self):
        # Normalize only if provided
        if self.name:
            normalized = self.name.strip().lower().capitalize()
        else:
            return  # Let Django show "This field is required."

        # Duplicate check only if directorate is selected
        if self.directorate_id and Department.objects.filter(
            directorate=self.directorate,
            name__iexact=normalized
        ).exclude(pk=self.pk).exists():
            raise ValidationError({
                "name": "This department already exists under this directorate."
            })

        # Assign normalized value so the form displays it
        self.name = normalized

    # -----------------------------
    # SAVE (DB‑safe normalization)
    # -----------------------------
    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().lower().capitalize()
        super().save(*args, **kwargs)

    # -----------------------------
    # SAFE __str__ (never crashes)
    # -----------------------------
    def __str__(self):
        return self.name or ""



class Office(LifeCycle):
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="offices"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["department", "name"],
                name="unique_office_per_department"
            )
        ]
        ordering = ["name"]

    # -----------------------------
    # VALIDATION (friendly errors)
    # -----------------------------
    def clean(self):
        # Normalize only if provided
        if self.name:
            normalized = self.name.strip().lower().capitalize()
        else:
            return  # Let Django show "This field is required."

        # Duplicate check only if department is selected
        if self.department_id and Office.objects.filter(
            department=self.department,
            name__iexact=normalized
        ).exclude(pk=self.pk).exists():
            raise ValidationError({
                "name": "This office already exists under this department."
            })

        # Assign normalized value so the form displays it
        self.name = normalized

    # -----------------------------
    # SAVE (DB‑safe normalization)
    # -----------------------------
    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().lower().capitalize()
        super().save(*args, **kwargs)

    # -----------------------------
    # SAFE __str__ (never crashes)
    # -----------------------------
    def __str__(self):
        return self.name or ""



# =====================================================
# USERS
# =====================================================
class User(LifeCycle):
    STATUS_CHOICES = [
        ("active",       "Active"),
        ("retired",      "Retired"),
        ("transferred",  "Transferred"),
    ]

    name    = models.CharField(max_length=200)
    surname = models.CharField(max_length=200)
    email   = models.EmailField(unique=True)
    phone   = models.CharField(max_length=20, blank=True, null=True)

    general_directorate = models.ForeignKey(
        GeneralDirectorate, on_delete=models.RESTRICT,
        related_name="users", null=True, blank=True
    )
    directorate = models.ForeignKey(
        Directorate, on_delete=models.CASCADE,
        related_name="users", null=True, blank=True
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE,
        related_name="users", null=True, blank=True
    )
    office = models.ForeignKey(
        Office, on_delete=models.CASCADE,
        related_name="users", null=True, blank=True
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    # ----------------------------------------------------
    # VALIDATION (friendly errors + hierarchy + email)
    # ----------------------------------------------------
    def clean(self):
        errors = {}

        # -------------------------
        # EMAIL NORMALIZATION
        # -------------------------
        if self.email:
            normalized_email = self.email.strip().lower()

            # Duplicate check (case-insensitive)
            if User.objects.filter(
                email__iexact=normalized_email
            ).exclude(pk=self.pk).exists():
                errors["email"] = "This email is already registered."

            self.email = normalized_email

        if errors:
            raise ValidationError(errors)

    # ----------------------------------------------------
    # SAVE (DB‑safe normalization)
    # ----------------------------------------------------
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} {self.surname}"



# =====================================================
# DEVICE (BASE)
# =====================================================
# Device uses multi-table inheritance — each subclass (DesktopComputer,
# LaptopComputer, etc.) gets its own DB table that extends this one.
# The base Device table holds all shared fields.
#
# Location follows the same pattern as Socket:
# a Device belongs to EITHER a Space OR a CommonArea — never both.
# Location follows the same pattern as Socket:
# a Device belongs to EITHER a Space OR a CommonArea — never both.
class Device(LifeCycle):
    USAGE_TYPE_CHOICES = [
        ("office",      "Office"),
        ("laboratory",  "Laboratory"),
        ("warehouse",   "Warehouse"),
        ("serverRoom",  "Server Room"),
    ]

    brand             = models.CharField(max_length=100)
    model             = models.CharField(max_length=100, blank=True, null=True)
    serial            = models.CharField(max_length=100, unique=True)
    registration_code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    ip_address        = models.CharField(max_length=100, blank=True, null=True, unique=True)
    mac_address       = models.CharField(max_length=50,  blank=True, null=True, unique=True)
    usage_type        = models.CharField(max_length=20, choices=USAGE_TYPE_CHOICES)

    # Physical location — exactly one must be set (enforced in clean()).
    space = models.ForeignKey(
        Space, null=True, blank=True, on_delete=models.CASCADE,
        related_name="devices",
        help_text="Space where this device is located (for regular offices/rooms)"
    )
    common_area = models.ForeignKey(
        "CommonArea", null=True, blank=True, on_delete=models.CASCADE,
        related_name="devices",
        help_text="Common area where this device is located (for corridors/shared spaces)"
    )

    # Which wall socket is this device plugged into? Completely optional.
    # SET_NULL: if the socket is deleted, the device stays but loses its socket reference.
    socket = models.ForeignKey(
        Socket, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="devices",
        help_text="Socket this device is plugged into (optional)"
    )

    class Meta:
        verbose_name = "Device"
        verbose_name_plural = "Devices"
        # Database-level constraint to guarantee uniqueness for assigned sockets
        constraints = [
            models.UniqueConstraint(
                fields=['socket'],
                name='unique_socket_per_device',
                condition=models.Q(socket__isnull=False)
            )
        ]

    def clean(self):
        super().clean()
        errors = {}

        # 1. Location structural validation (Existing)
        if not self.space and not self.common_area:
            errors["__all__"] = "Either a Space or a Common Area must be defined."
        if self.space and self.common_area:
            errors["__all__"] = "A Space and a Common Area cannot both be defined at the same time."

        # 2. Socket validations (Uniqueness & Building validation)
        if self.socket:
            if self.space_id and self.socket.space_id != self.space_id:
                errors["socket"] = "The selected socket does not belong to this space."
            elif self.common_area_id and self.socket.common_area_id != self.common_area_id:
                errors["socket"] = "The selected socket does not belong to this common area."

            # Check if socket is already taken by another device
            duplicate_device = Device.objects.filter(socket=self.socket).exclude(pk=self.pk)
            if duplicate_device.exists():
                other_device = duplicate_device.first().get_specific_device()
                errors["socket"] = f"This socket is already in use by another device ({other_device})."

            # Determine socket's building based on its location link
            socket_building = None
            if hasattr(self.socket, 'space') and self.socket.space:
                socket_building = self.socket.space.building
            elif hasattr(self.socket, 'common_area') and self.socket.common_area:
                socket_building = self.socket.common_area.floor.building

            # Compare with the device's building using the existing @property
            device_building = self.building
            if device_building and socket_building and device_building != socket_building:
                errors["socket"] = (
                    f"Location mismatch! The device is in building '{device_building}', "
                    f"but the selected socket belongs to building '{socket_building}'."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def room(self):
        # Only meaningful if in a Space — CommonArea devices have no Room.
        return self.space.room if self.space else None

    @property
    def floor(self):
        if self.space:
            return self.space.floor
        if self.common_area:
            return self.common_area.floor
        return None

    @property
    def building(self):
        if self.space:
            return self.space.building
        if self.common_area:
            return self.common_area.floor.building
        return None

    @property
    def location(self):
        """Human-readable location string regardless of Space or CommonArea."""
        if self.space:
            return f"{self.space.building} / {self.space.floor} / {self.room} / {self.space}"
        if self.common_area:
            return self.common_area
        return ""

    def get_specific_device(self):
        """
        Multi-table inheritance means the base Device row doesn't know its own type.
        This walks the possible child attributes to find the actual subclass instance
        (e.g. DesktopComputer, Printer) so type-specific fields can be accessed.
        Returns self (base Device) if no subclass is found.
        """
        for attr in ['laptopcomputer', 'desktopcomputer', 'allinonecomputer',
                     'servercomputer', 'printer', 'ups', 'accesspoint',
                     'switch', 'phone']:
            if hasattr(self, attr):
                return getattr(self, attr)
        return self

    def __str__(self):
        return f"{self.brand} - {self.serial}"




# =====================================================
# DEVICE SUBCLASSES (Multi-table Inheritance)
# =====================================================
# Each subclass adds only the fields specific to that device type.
# All shared fields (brand, serial, location, etc.) live on Device.
# Django creates a separate DB table for each subclass, linked to Device via a 1-to-1.

class DesktopComputer(Device):
    device_label = "Desktop"  # Class-level label used in the admin display
    cpu        = models.CharField(max_length=100)
    ram_gb     = models.IntegerField()
    storage_gb = models.IntegerField()
    pid = models.CharField(max_length=100, blank=True, null=True)  # Optional Product ID for software licensing


class AllInOneComputer(Device):
    device_label = "All-in-One"
    cpu         = models.CharField(max_length=100)
    ram_gb      = models.IntegerField()
    storage_gb  = models.IntegerField()
    screen_size = models.CharField(max_length=10)
    pid = models.CharField(max_length=100, blank=True, null=True)  # Optional Product ID for software licensing


class LaptopComputer(Device):
    device_label = "Laptop"
    cpu         = models.CharField(max_length=100)
    ram_gb      = models.IntegerField()
    storage_gb  = models.IntegerField()
    screen_size = models.CharField(max_length=10)
    battery_capacity = models.CharField(max_length=50)  # e.g. "50Wh", "4000mAh"
    pid = models.CharField(max_length=100, blank=True, null=True)  # Optional Product ID for software licensing


class ServerComputer(Device):
    device_label = "Server"
    rack_unit = models.CharField(max_length=50)  # e.g. "1U", "2U"


class Printer(Device):
    device_label = "Printer"
    PRINTER_TYPE_CHOICES = [
        ("laser",         "Laser"),
        ("inkjet",        "Inkjet"),
        ("multifunction", "Multifunction"),
    ]
    printer_type = models.CharField(max_length=20, choices=PRINTER_TYPE_CHOICES)


class Ups(Device):
    device_label = "UPS"
    capacity_va = models.IntegerField()  # Power capacity in volt-amperes

    class Meta:
        verbose_name = "UPS"
        verbose_name_plural = "UPS units"


class Switch(Device):
    device_label = "Switch"
    SWITCH_LAYER_CHOICES = [
        ("L2",    "Layer 2"),
        ("L3",    "Layer 3"),
        ("L2+L3", "Layer 2 + Layer 3"),
    ]
    layer_capability = models.CharField(max_length=10, choices=SWITCH_LAYER_CHOICES, default="L2")
    total_ports      = models.IntegerField()
    poe_supported    = models.BooleanField(default=False)  # Power over Ethernet capable?
    poe_budget_watts = models.IntegerField(null=True, blank=True)
    uplink_speed     = models.CharField(max_length=20, blank=True, null=True)
    downlink_speed   = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Switch {self.brand} {self.model or ''} (SN: {self.serial})"


class AccessPoint(Device):
    device_label = "Access Point"
    gps_lat = models.FloatField(null=True, blank=True)  # Optional GPS coordinates
    gps_lon = models.FloatField(null=True, blank=True)  # useful for mapping APs on a floor plan



class Phone(Device):
    device_label = "Phone"
    PHONE_TYPE_CHOICES = [
        ("analog",  "Analog"),
        ("digital", "Digital"),
    ]
    phone_type = models.CharField(max_length=20, choices=PHONE_TYPE_CHOICES)
    phone_number = models.IntegerField(blank=True, null=True)  # Optional direct line number



# =====================================================
# PERIPHERALS
# =====================================================
# A Peripheral (keyboard, monitor, mouse) belongs to a specific Device.
# CASCADE means: if the Device is deleted, all its peripherals are deleted too.
class Peripheral(LifeCycle):
    PERIPHERAL_TYPE_CHOICES = [
        ("keyboard", "Keyboard"),
        ("monitor",  "Monitor"),
        ("mouse",    "Mouse"),
    ]
    device          = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="peripherals")
    peripheral_type = models.CharField(max_length=20, choices=PERIPHERAL_TYPE_CHOICES)
    brand           = models.CharField(max_length=100, blank=True, null=True)
    model           = models.CharField(max_length=100, blank=True, null=True)
    serial_number   = models.CharField(max_length=100, unique=True, blank=True, null=True)
    specifications  = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.peripheral_type} ({self.device})"


# =====================================================
# ASSIGNMENTS
# =====================================================
# An Assignment records which User is using which Device, and when.
# A device can have multiple assignments over time (primary, shared, temporary).
#
# Note: Assignment does NOT extend LifeCycle — it uses its own date fields
# (assignment_date, end_date) rather than valid_from/valid_to.


class Assignment(models.Model):
    ASSIGNMENT_TYPE_CHOICES = [
        ("primary",   "Primary"),
        ("shared",    "Shared"),
        ("temporary", "Temporary"),
    ]

    user            = models.ForeignKey("User", on_delete=models.CASCADE)
    device          = models.ForeignKey("Device", on_delete=models.CASCADE, related_name="assignments")
    assignment_date = models.DateField()
    end_date        = models.DateField(blank=True, null=True)
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPE_CHOICES, default="primary")
    notes           = models.TextField(blank=True, null=True)

    # ============================================================
    # CLEAN VALIDATION (FINAL VERSION)
    # ============================================================
    def clean(self):
        errors = {}

        # ------------------------------------------------
        # BASIC REQUIRED CHECKS
        # ------------------------------------------------
        if not self.device_id or not self.user_id or not self.assignment_date:
            return

        # Normalize open-ended for Python logic
        self_end = self.end_date or date(9999, 12, 31)

        # ------------------------------------------------
        # 1. End date cannot be before start date
        # ------------------------------------------------
        if self.end_date and self.end_date < self.assignment_date:
            errors["end_date"] = "End date cannot  be before assignment date."

        # ------------------------------------------------
        # 2. SHARED MODE RULES
        # ------------------------------------------------
        shared_exists = Assignment.objects.filter(
            device=self.device,
            assignment_type="shared"
        ).exclude(pk=self.pk).exists()

        if shared_exists and self.assignment_type != "shared":
            errors["assignment_type"] = (
                "This device is already shared. All assignments must be shared."
            )

        if self.assignment_type == "shared":
            primary_exists = Assignment.objects.filter(
                device=self.device,
                assignment_type="primary"
            ).exclude(pk=self.pk).exists()

            if primary_exists:
                errors["assignment_type"] = (
                    "This device has a primary assignment. "
                    "It cannot be shared until the primary is removed."
                )

        # ------------------------------------------------
        # 3. PRIMARY OVERLAP (DEVICE LEVEL)
        # ------------------------------------------------
        if self.assignment_type == "primary":
            overlapping_device = Assignment.objects.annotate(
                normalized_end=Coalesce("end_date", Value(date(9999, 12, 31)))
            ).filter(
                device=self.device,
                assignment_type="primary",
                assignment_date__lte=self_end,
                normalized_end__gte=self.assignment_date,
            ).exclude(pk=self.pk)

            if overlapping_device.exists():
                errors["assignment_date"] = (
                    "This device already has a primary assignment during this period."
                )

        # ------------------------------------------------
        # 4. PRIMARY <-> TEMPORARY OVERLAP (SAME USER + SAME DEVICE)
        # ------------------------------------------------
        if self.assignment_type in ("primary", "temporary"):
            overlapping_user_mixed = Assignment.objects.annotate(
                normalized_end=Coalesce("end_date", Value(date(9999, 12, 31)))
            ).filter(
                user=self.user,
                device=self.device,
                assignment_type__in=["primary", "temporary"],
                assignment_date__lte=self_end,
                normalized_end__gte=self.assignment_date,
            ).exclude(pk=self.pk)

            if overlapping_user_mixed.exists():
                errors["assignment_date"] = (
                    "This user already has a primary or temporary assignment for this device "
                    "during the selected period."
                )

        # ------------------------------------------------
        # FINAL ERROR RAISE
        # ------------------------------------------------
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.user} → {self.device} ({self.assignment_type})"
