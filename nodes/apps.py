from django.apps import AppConfig

class NodesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nodes'
    label = 'nodes'

    def ready(self):
        # IMPORT watson.search instead of plain watson
        from watson import search as watson
        
        from .models import (
            City, Area, Building, Floor, CommonArea, Room, Space, Socket,
            GeneralDirectorate, Directorate, Department, Office, User,
            Device, DesktopComputer, AllInOneComputer, LaptopComputer,
            ServerComputer, Printer, Ups, Switch, AccessPoint, Phone, Peripheral,
            Assignment
        )

        # Register only fields that actually exist on the current models.
        watson.register(City, fields=('name',))
        watson.register(Area, fields=('name',))
        watson.register(Building, fields=('name', 'address'))
        watson.register(Floor, fields=('floor_number',))
        watson.register(CommonArea, fields=('name', 'area_type'))
        watson.register(Room, fields=('room_code',))
        watson.register(Space, fields=('name',))
        watson.register(Socket, fields=('socket_code',))

        watson.register(GeneralDirectorate, fields=('name',))
        watson.register(Directorate, fields=('name',))
        watson.register(Department, fields=('name',))
        watson.register(Office, fields=('name',))

        watson.register(User, fields=('name', 'surname', 'email', 'phone'))

        watson.register(Device, fields=('brand', 'model', 'serial', 'registration_code', 'ip_address', 'mac_address', 'usage_type'))
        watson.register(DesktopComputer, fields=('cpu', 'ram_gb', 'storage_gb'))
        watson.register(AllInOneComputer, fields=('cpu', 'ram_gb', 'storage_gb', 'screen_size'))
        watson.register(LaptopComputer, fields=('cpu', 'ram_gb', 'storage_gb', 'screen_size'))
        watson.register(ServerComputer, fields=('rack_unit',))
        watson.register(Printer, fields=('printer_type',))
        watson.register(Ups, fields=('capacity_va',))
        watson.register(Switch, fields=('layer_capability', 'uplink_speed', 'downlink_speed'))
        watson.register(AccessPoint, fields=('gps_lat', 'gps_lon'))
        watson.register(Phone, fields=('phone_type',))
        watson.register(Peripheral, fields=('peripheral_type', 'brand', 'model', 'serial_number', 'specifications'))

        watson.register(Assignment, fields=('assignment_type', 'notes'))