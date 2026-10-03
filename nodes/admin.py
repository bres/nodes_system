from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import (
    # Geography
    City, Area, Building, Floor, Room, Space, CommonArea,

    # Organization
    GeneralDirectorate, Directorate, Department, Office,

    # Infrastructure
    Socket,

    # Users
    User,

    # Devices
    Device,
    DesktopComputer,
    AllInOneComputer,
    LaptopComputer,
    ServerComputer,
    Printer,
    Ups,
    AccessPoint,
    Switch,
    Phone,

    # Peripherals
    Peripheral,

    # Assignments
    Assignment,
)


# =====================================================
# BASE ADMIN
# =====================================================

class LifeCycleAdmin(admin.ModelAdmin):
    list_filter = ("is_active",)
    readonly_fields = ("valid_from",)


# =====================================================
# INLINES
# =====================================================

class SocketInline(admin.TabularInline):
    model = Socket
    extra = 1
    fields = ("socket_code", "is_active")   # only show what makes sense
    readonly_fields = ("valid_from",)



class PeripheralInline(admin.TabularInline):
    model = Peripheral
    extra = 0


# =====================================================
# GEOGRAPHY
# =====================================================

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "city")
    list_filter = ("city",)
    search_fields = ("name", "city__name")


@admin.register(Building)
class BuildingAdmin(LifeCycleAdmin):
    list_display = ("name", "area", "address","postal_code", "is_active")
    list_filter = ("area__city", "is_active")
    search_fields = ("name", "address","postal_code")


@admin.register(Floor)
class FloorAdmin(LifeCycleAdmin):
    list_display = ("building", "floor_number", "is_active")
    list_filter = ("building", "is_active")
    search_fields = ("building__name",)


@admin.register(Room)
class RoomAdmin(LifeCycleAdmin):
    list_display = ("room_code", "floor", "get_building", "is_active")
    search_fields = ("room_code", "floor__building__name")
    list_filter = ("floor__building", "is_active")

    @admin.display(description="Building", ordering="floor__building__name")
    def get_building(self, obj):
        return obj.floor.building if obj.floor_id else "-"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("floor__building__area__city")


@admin.register(Space)
class SpaceAdmin(LifeCycleAdmin):
    autocomplete_fields = ("room",)
    list_display = ("name", "room", "get_floor", "get_building", "is_active")  # removed position_index
    list_filter = ("room__floor__building", "is_active")
    search_fields = ("name", "room__room_code")
    inlines = [SocketInline]

    # removed position_index from readonly_fields
    readonly_fields = ("valid_from",)

    @admin.display(description="Floor", ordering="room__floor__floor_number")
    def get_floor(self, obj):
        return f"Floor {obj.room.floor.floor_number}"

    @admin.display(description="Building", ordering="room__floor__building__name")
    def get_building(self, obj):
        return obj.room.floor.building.name

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "room__floor__building__area"
        )

    def save_formset(self, request, form, formset, change):
        formset.save()


@admin.register(CommonArea)
class CommonAreaAdmin(LifeCycleAdmin):
    list_display = ("name", "area_type", "get_floor", "get_building", "is_active")
    list_filter = ("area_type", "floor__building", "is_active")
    search_fields = ("name", "floor__building__name")
    inlines = [SocketInline]

    @admin.display(description="Floor", ordering="floor__floor_number")
    def get_floor(self, obj):
        return f"Floor {obj.floor.floor_number}"

    @admin.display(description="Building", ordering="floor__building__name")
    def get_building(self, obj):
        return obj.floor.building.name

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("floor__building__area__city")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):   # add this
        if db_field.name == "floor":
            kwargs["queryset"] = (
                Floor.objects
                .select_related("building__area__city")
                .filter(is_active=True)
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# =====================================================
# ORGANIZATION
# =====================================================

@admin.register(GeneralDirectorate)
class GeneralDirectorateAdmin(LifeCycleAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(Directorate)
class DirectorateAdmin(LifeCycleAdmin):
    list_display = ("name", "general_directorate", "is_active")
    list_filter = ("general_directorate", "is_active")
    search_fields = ("name", "general_directorate__name")


@admin.register(Department)
class DepartmentAdmin(LifeCycleAdmin):
    list_display = ("name", "directorate", "is_active")
    list_filter = ("directorate__general_directorate", "is_active")
    search_fields = ("name", "directorate__name")


@admin.register(Office)
class OfficeAdmin(LifeCycleAdmin):
    list_display = ("name", "department", "is_active")
    list_filter = ("department__directorate", "is_active")
    search_fields = ("name", "department__name")


# =====================================================
# INFRASTRUCTURE
# =====================================================

@admin.register(Socket)
class SocketAdmin(LifeCycleAdmin):
    exclude = ("building",)
    list_display = ("socket_code", "get_location", "get_building", "is_active")
    list_filter = ("is_active",)
    search_fields = ("socket_code", "space__name", "common_area__name")

    @admin.display(description="Location")
    def get_location(self, obj):
        return obj.location

    @admin.display(description="Building")
    def get_building(self, obj):
        return obj.building

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "space__room__floor__building",
            "common_area__floor__building",
        )


# =====================================================
# DEVICES
# =====================================================

def _device_label(obj):
    specific = obj.get_specific_device()
    return getattr(specific, "device_label", "Device")


def _device_location(obj):
    """Return the Space or CommonArea that is set."""
    if obj.space:
        return f"Space: {obj.space}"
    if obj.common_area:
        return f"CommonArea: {obj.common_area}"
    return "—"


@admin.register(Device)
class DeviceAdmin(LifeCycleAdmin):
    list_display = ("brand", "model", "serial", "get_device_label", "usage_type", "get_location", "is_active")
    search_fields = ("brand", "serial", "registration_code", "model")
    list_filter = ("usage_type", "is_active")
    inlines = [PeripheralInline]

    @admin.display(description="Device Type")
    def get_device_label(self, obj):
        return _device_label(obj)

    @admin.display(description="Location")
    def get_location(self, obj):
        return _device_location(obj)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "space", "common_area",
            "laptopcomputer", "desktopcomputer", "allinonecomputer",
            "servercomputer", "printer", "ups",
            "accesspoint", "switch", "phone",
        )


@admin.register(DesktopComputer)
class DesktopComputerAdmin(LifeCycleAdmin):
    list_display = ("brand", "serial", "cpu", "ram_gb", "storage_gb", "get_location", "is_active")
    search_fields = ("brand", "serial", "registration_code", "model")
    list_filter = ("usage_type", "is_active")
    inlines = [PeripheralInline]

    @admin.display(description="Location")
    def get_location(self, obj):
        return _device_location(obj)


@admin.register(AllInOneComputer)
class AllInOneComputerAdmin(LifeCycleAdmin):
    list_display = ("brand", "serial", "cpu", "ram_gb", "storage_gb", "screen_size", "get_location", "is_active")
    search_fields = ("brand", "serial", "registration_code", "model")
    list_filter = ("usage_type", "is_active")
    inlines = [PeripheralInline]

    @admin.display(description="Location")
    def get_location(self, obj):
        return _device_location(obj)


@admin.register(LaptopComputer)
class LaptopComputerAdmin(LifeCycleAdmin):
    list_display = ("brand", "serial", "cpu", "ram_gb", "storage_gb", "screen_size", "get_location", "is_active")
    search_fields = ("brand", "serial", "registration_code", "model")
    list_filter = ("usage_type", "is_active")
    inlines = [PeripheralInline]

    @admin.display(description="Location")
    def get_location(self, obj):
        return _device_location(obj)


@admin.register(ServerComputer)
class ServerComputerAdmin(LifeCycleAdmin):
    list_display = ("brand", "serial", "rack_unit", "get_location", "is_active")
    search_fields = ("brand", "serial", "registration_code", "model")
    list_filter = ("usage_type", "is_active")
    inlines = [PeripheralInline]

    @admin.display(description="Location")
    def get_location(self, obj):
        return _device_location(obj)


@admin.register(Printer)
class PrinterAdmin(LifeCycleAdmin):
    list_display = ("brand", "serial", "printer_type", "get_location", "is_active")
    search_fields = ("brand", "serial", "registration_code", "model")
    list_filter = ("printer_type", "usage_type", "is_active")
    inlines = [PeripheralInline]

    @admin.display(description="Location")
    def get_location(self, obj):
        return _device_location(obj)


@admin.register(Ups)
class UPSAdmin(LifeCycleAdmin):
    list_display = ("brand", "serial", "capacity_va", "get_location", "is_active")
    search_fields = ("brand", "serial", "registration_code", "model")
    list_filter = ("usage_type", "is_active")
    inlines = [PeripheralInline]

    @admin.display(description="Location")
    def get_location(self, obj):
        return _device_location(obj)


@admin.register(AccessPoint)
class AccessPointAdmin(LifeCycleAdmin):
    list_display = ("brand", "serial", "gps_lat", "gps_lon", "get_location", "is_active")
    search_fields = ("brand", "serial", "registration_code", "model")
    list_filter = ("usage_type", "is_active")
    inlines = [PeripheralInline]

    @admin.display(description="Location")
    def get_location(self, obj):
        return _device_location(obj)


@admin.register(Switch)
class SwitchAdmin(LifeCycleAdmin):
    list_display = (
        "brand", "serial", "layer_capability", "total_ports",
        "poe_supported", "uplink_speed", "downlink_speed", "get_location", "is_active",
    )
    search_fields = ("brand", "serial", "registration_code", "model")
    list_filter = ("layer_capability", "poe_supported", "usage_type", "is_active")
    inlines = [PeripheralInline]

    @admin.display(description="Location")
    def get_location(self, obj):
        return _device_location(obj)


@admin.register(Phone)
class PhoneAdmin(LifeCycleAdmin):
    list_display = ("brand", "serial", "phone_type", "get_location", "is_active")
    search_fields = ("brand", "serial", "registration_code", "model")
    list_filter = ("phone_type", "usage_type", "is_active")
    inlines = [PeripheralInline]

    @admin.display(description="Location")
    def get_location(self, obj):
        return _device_location(obj)


@admin.register(Peripheral)
class PeripheralAdmin(LifeCycleAdmin):
    list_display = ("peripheral_type", "device", "brand", "model", "serial_number", "is_active")
    list_filter = ("peripheral_type", "is_active")
    search_fields = ("serial_number", "brand", "model", "device__serial")


# =====================================================
# USERS
# =====================================================

@admin.register(User)
class UserAdmin(LifeCycleAdmin):
    list_display = (
        "name", "surname", "email", "status",
        "general_directorate", "department", "office", "is_active",
    )
    search_fields = ("name", "surname", "email")
    list_filter = ("status", "is_active", "general_directorate")
    fieldsets = (
        ("👤 User Details", {
            "fields": ("name", "surname", "email", "phone", "status")
        }),
        ("🏢 Organizational Hierarchy", {
            "description": (
                "Select from top to bottom. "
                "Each level must belong to the level above it."
            ),
            "fields": (
                "general_directorate",
                "directorate",
                "department",
                "office",
            )
        }),
        ("🕒 LifeCycle", {
            "classes": ("collapse",),
            "fields": ("is_active", "valid_from", "valid_to")
        }),
    )


# =====================================================
# ASSIGNMENTS
# =====================================================

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "user", "device", "get_device_label",
        "assignment_type", "assignment_date", "end_date",
    )
    list_filter = ("assignment_type",)
    date_hierarchy = "assignment_date"
    search_fields = ("user__name", "user__surname", "device__serial", "device__brand")
    autocomplete_fields = ("user", "device")

    @admin.display(description="Device Type")
    def get_device_label(self, obj):
        return _device_label(obj.device)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "user",
            "device__space",
            "device__common_area",
            "device__laptopcomputer",
            "device__desktopcomputer",
            "device__allinonecomputer",
            "device__servercomputer",
            "device__printer",
            "device__ups",
            "device__accesspoint",
            "device__switch",
            "device__phone",
        )