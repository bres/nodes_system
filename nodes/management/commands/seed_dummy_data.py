from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from nodes.models import (
    AccessPoint,
    AllInOneComputer,
    Area,
    Assignment,
    Building,
    City,
    CommonArea,
    Department,
    DesktopComputer,
    Device,
    Directorate,
    Floor,
    GeneralDirectorate,
    LaptopComputer,
    Office,
    Peripheral,
    Phone,
    Printer,
    Room,
    ServerComputer,
    Socket,
    Space,
    Switch,
    Ups,
    User,
)


class Command(BaseCommand):
    help = "Create realistic dummy data for all inventory models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing records before creating dummy data.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.reset_database()

        with transaction.atomic():
            self.create_dummy_data()

        self.stdout.write(
            self.style.SUCCESS("Dummy data creation finished successfully.")
        )

    def reset_database(self):
        models_in_reverse_order = [
            Assignment,
            Peripheral,
            AccessPoint,
            AllInOneComputer,
            DesktopComputer,
            LaptopComputer,
            Printer,
            ServerComputer,
            Switch,
            Ups,
            Phone,
            User,
            Office,
            Department,
            Directorate,
            GeneralDirectorate,
            Socket,
            Space,
            Room,
            CommonArea,
            Floor,
            Building,
            Area,
            City,
        ]

        for model in models_in_reverse_order:
            model.objects.all().delete()

        self.stdout.write(self.style.WARNING("Existing data has been cleared."))

    def create_dummy_data(self):
        self.stdout.write("Creating geographic structure...")
        cities = self.create_cities()
        areas = self.create_areas(cities)
        buildings = self.create_buildings(areas)
        floors = self.create_floors(buildings)
        common_areas = self.create_common_areas(floors)
        rooms = self.create_rooms(floors)
        spaces = self.create_spaces(rooms)
        sockets = self.create_sockets(spaces, common_areas, buildings)

        self.stdout.write("Creating organizational structure...")
        general_directorates = self.create_general_directorates()
        directorates = self.create_directorates(general_directorates)
        departments = self.create_departments(directorates)
        offices = self.create_offices(departments)
        users = self.create_users(offices, directorates, departments, general_directorates)

        self.stdout.write("Creating devices and peripherals...")
        devices = self.create_devices(spaces, common_areas, sockets)
        devices.extend(self.create_additional_network_devices(common_areas, sockets))
        self.create_peripherals(devices)

        self.stdout.write("Creating assignments...")
        self.create_assignments(users, devices)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created data for {len(cities)} cities, {len(areas)} areas, "
                f"{len(buildings)} buildings, {len(floors)} floors, {len(rooms)} rooms, "
                f"{len(spaces)} spaces, {len(sockets)} sockets, {len(general_directorates)} "
                f"general directorates, {len(directorates)} directorates, {len(departments)} "
                f"departments, {len(offices)} offices, {len(users)} users, and {len(devices)} devices."
            )
        )

    def create_cities(self):
        names = ["Athens", "Thessaloniki", "Patras"]
        objects = []
        for name in names:
            city = City(name=name)
            city.full_clean()
            city.save()
            objects.append(city)
        return objects

    def create_areas(self, cities):
        area_map = {
            "Athens": ["Kolonaki", "Piraeus", "Kallithea"],
            "Thessaloniki": ["Center", "Seychelles", "Kalamaria"],
            "Patras": ["Downtown", "Agyia", "Rio"],
        }

        objects = []
        for city in cities:
            for area_name in area_map.get(city.name, []):
                area = Area(city=city, name=area_name)
                area.full_clean()
                area.save()
                objects.append(area)
        return objects

    def create_buildings(self, areas):
        objects = []
        for idx, area in enumerate(areas, start=1):
            building_name = f"{area.name} HQ {idx % 3 + 1}"
            building = Building(
                area=area,
                name=building_name,
                address=f"{idx} {area.name} Street",
                postal_code=f"10{idx:03d}",
                valid_from=date(2020, 1, 1),
                valid_to=None,
                is_active=True,
            )
            building.full_clean()
            building.save()
            objects.append(building)
        return objects

    def create_floors(self, buildings):
        objects = []
        for building in buildings:
            for floor_number in [-1, 0, 1, 2, 3, 4]:
                floor = Floor(
                    building=building,
                    floor_number=floor_number,
                    valid_from=date(2020, 1, 1),
                    valid_to=None,
                    is_active=True,
                )
                floor.full_clean()
                floor.save()
                objects.append(floor)
        return objects

    def create_common_areas(self, floors):
        area_types = ["corridor", "lobby", "server_room", "other"]
        objects = []
        for floor in floors:
            for idx, area_type in enumerate(area_types[:2], start=1):
                common_area = CommonArea(
                    floor=floor,
                    name=f"{area_type.title()} {idx}",
                    area_type=area_type,
                    valid_from=date(2020, 1, 1),
                    valid_to=None,
                    is_active=True,
                )
                common_area.full_clean()
                common_area.save()
                objects.append(common_area)
        return objects

    def create_rooms(self, floors):
        objects = []
        for floor in floors:
            for room_index in range(1, 4):
                room = Room(
                    floor=floor,
                    room_code=f"R{floor.floor_number + 10:02d}{room_index}",
                    valid_from=date(2020, 1, 1),
                    valid_to=None,
                    is_active=True,
                )
                room.full_clean()
                room.save()
                objects.append(room)
        return objects

    def create_spaces(self, rooms):
        objects = []
        for room in rooms:
            for space_index in range(1, 3):
                space = Space(
                    room=room,
                    name=f"Desk {space_index}",
                    valid_from=date(2020, 1, 1),
                    valid_to=None,
                    is_active=True,
                )
                space.full_clean()
                space.save()
                objects.append(space)
        return objects

    def create_sockets(self, spaces, common_areas, buildings):
        objects = []
        building_sockets = {}

        for building in buildings:
            building_sockets[building.pk] = 0

        for space in spaces[:15]:
            building = space.room.floor.building
            building_sockets.setdefault(building.pk, 0)
            building_sockets[building.pk] += 1
            socket_code = f"{building.name[:2].upper()}-{building_sockets[building.pk]:02d}"
            socket = Socket(
                socket_code=socket_code,
                space=space,
                common_area=None,
                building=building,
            )
            socket.full_clean()
            socket.save()
            objects.append(socket)

        for common_area in common_areas[:10]:
            building = common_area.floor.building
            building_sockets.setdefault(building.pk, 0)
            building_sockets[building.pk] += 1
            socket_code = f"{building.name[:2].upper()}-{building_sockets[building.pk]:02d}"
            socket = Socket(
                socket_code=socket_code,
                space=None,
                common_area=common_area,
                building=building,
            )
            socket.full_clean()
            socket.save()
            objects.append(socket)

        return objects

    def create_general_directorates(self):
        names = [
            "Ministry of Digital Governance",
            "General Directorate of Infrastructure",
            "General Directorate of Administration",
        ]
        objects = []
        for name in names:
            obj = GeneralDirectorate(name=name)
            obj.full_clean()
            obj.save()
            objects.append(obj)
        return objects

    def create_directorates(self, general_directorates):
        objects = []
        patterns = [
            ("Ministry of Digital Governance", ["IT Services", "Cybersecurity"]),
            ("General Directorate of Infrastructure", ["Network Services", "Facilities"]),
            ("General Directorate of Administration", ["Human Resources", "Procurement"]),
        ]

        for general_directorate in general_directorates:
            directorates = patterns[[gd.name for gd in general_directorates].index(general_directorate.name)][1]
            for directorate_name in directorates:
                obj = Directorate(
                    name=directorate_name,
                    general_directorate=general_directorate,
                )
                obj.full_clean()
                obj.save()
                objects.append(obj)
        return objects

    def create_departments(self, directorates):
        objects = []
        dept_map = {
            "IT Services": ["Support", "Applications"],
            "Cybersecurity": ["Security Operations", "Governance"],
            "Network Services": ["Core Infrastructure", "WAN Management"],
            "Facilities": ["Building Systems", "Maintenance"],
            "Human Resources": ["Recruitment", "Training"],
            "Procurement": ["Supplies", "Contracts"],
        }

        for directorate in directorates:
            for dept_name in dept_map.get(directorate.name, ["Operations"]):
                obj = Department(name=dept_name, directorate=directorate)
                obj.full_clean()
                obj.save()
                objects.append(obj)
        return objects

    def create_offices(self, departments):
        objects = []
        for department in departments:
            for office_index in range(1, 3):
                office = Office(
                    name=f"{department.name} Office {office_index}",
                    department=department,
                )
                office.full_clean()
                office.save()
                objects.append(office)
        return objects

    def create_users(self, offices, directorates, departments, general_directorates):
        first_names = [
            "Nikos", "Maria", "Alex", "Dora", "Panos", "Eleni",
            "George", "Katerina", "Thanasis", "Sofia", "Petros", "Anna",
        ]
        last_names = [
            "Papadopoulos", "Kostopoulos", "Androulakis", "Mavrommati",
            "Iliadis", "Georgiou", "Kontos", "Nikolaou", "Katsaros",
            "Vasilopoulou", "Dimitriou", "Raptis",
        ]

        objects = []
        office_index = 0
        for office in offices:
            department = office.department
            directorate = department.directorate
            general_directorate = directorate.general_directorate
            for idx in range(2):
                first_name = first_names[office_index % len(first_names)]
                last_name = last_names[(office_index + idx) % len(last_names)]
                email = f"{first_name.lower()}.{last_name.lower()}@{general_directorate.name.lower().replace(' ', '')}.gr"
                organization_fields = {
                    "general_directorate": None,
                    "directorate": None,
                    "department": None,
                    "office": None,
                }
                assignment_level = (office_index + idx) % 4
                organization_fields[
                    ["general_directorate", "directorate", "department", "office"][assignment_level]
                ] = [general_directorate, directorate, department, office][assignment_level]
                user = User(
                    name=first_name,
                    surname=last_name,
                    email=email,
                    phone=f"690{(office_index + idx) * 123456:08d}",
                    **organization_fields,
                    status="active",
                    valid_from=date(2021, 1, 1),
                    valid_to=None,
                    is_active=True,
                )
                user.full_clean()
                user.save()
                objects.append(user)
                office_index += 1
        return objects

    def create_devices(self, spaces, common_areas, sockets):
        device_specs = []

        # Desktop computers in spaces
        for index, space in enumerate(spaces[:6], start=1):
            socket = next((s for s in sockets if s.space_id == space.pk), None)
            device_specs.append(
                (
                    DesktopComputer,
                    {
                        "brand": "Dell",
                        "model": "OptiPlex 7090",
                        "serial": f"DT-{index:04d}",
                        "registration_code": f"REG-DT-{index:04d}",
                        "mac_address": f"00:1A:2B:{index:02d}:3C:{index:02d}",
                        "usage_type": "office",
                        "space": space,
                        "common_area": None,
                        "socket": socket,
                        "cpu": "Intel Core i7",
                        "ram_gb": 16,
                        "storage_gb": 512,
                        "pid": f"PID-DT-{index:04d}",
                    },
                )
            )

        # Laptops
        for index, space in enumerate(spaces[6:12], start=1):
            socket = next((s for s in sockets if s.space_id == space.pk), None)
            device_specs.append(
                (
                    LaptopComputer,
                    {
                        "brand": "Lenovo",
                        "model": "ThinkPad T14",
                        "serial": f"LT-{index:04d}",
                        "registration_code": f"REG-LT-{index:04d}",
                        "mac_address": f"00:1A:2B:{index + 10:02d}:5C:{index:02d}",
                        "usage_type": "office",
                        "space": space,
                        "common_area": None,
                        "socket": socket,
                        "cpu": "Intel Core i5",
                        "ram_gb": 16,
                        "storage_gb": 512,
                        "screen_size": "14\"",
                        "battery_capacity": "52Wh",
                        "pid": f"PID-LT-{index:04d}",
                    },
                )
            )

        # AIO devices
        for index, space in enumerate(spaces[12:15], start=1):
            socket = next((s for s in sockets if s.space_id == space.pk), None)
            device_specs.append(
                (
                    AllInOneComputer,
                    {
                        "brand": "HP",
                        "model": "EliteOne 840 G9",
                        "serial": f"AI-{index:04d}",
                        "registration_code": f"REG-AI-{index:04d}",
                        "mac_address": f"00:1A:2B:{index + 20:02d}:7C:{index:02d}",
                        "usage_type": "office",
                        "space": space,
                        "common_area": None,
                        "socket": socket,
                        "cpu": "Intel Core i7",
                        "ram_gb": 32,
                        "storage_gb": 1024,
                        "screen_size": "23.8\"",
                        "pid": f"PID-AI-{index:04d}",
                    },
                )
            )

        # Server computers
        for index, common_area in enumerate(common_areas[:2], start=1):
            socket = next((s for s in sockets if s.common_area_id == common_area.pk), None)
            device_specs.append(
                (
                    ServerComputer,
                    {
                        "brand": "Dell",
                        "model": "PowerEdge R750",
                        "serial": f"SR-{index:04d}",
                        "registration_code": f"REG-SR-{index:04d}",
                        "mac_address": f"00:1A:2B:{index + 30:02d}:9C:{index:02d}",
                        "usage_type": "serverRoom",
                        "space": None,
                        "common_area": common_area,
                        "socket": socket,
                        "rack_unit": "2U",
                    },
                )
            )

        # Printers
        for index, common_area in enumerate(common_areas[2:5], start=1):
            socket = next((s for s in sockets if s.common_area_id == common_area.pk), None)
            device_specs.append(
                (
                    Printer,
                    {
                        "brand": "Canon",
                        "model": "imageRUNNER ADVANCE",
                        "serial": f"PR-{index:04d}",
                        "registration_code": f"REG-PR-{index:04d}",
                        "mac_address": f"00:1A:2B:{index + 40:02d}:AA:{index:02d}",
                        "usage_type": "warehouse",
                        "space": None,
                        "common_area": common_area,
                        "socket": socket,
                        "printer_type": "multifunction",
                    },
                )
            )

        # UPS
        for index, common_area in enumerate(common_areas[5:7], start=1):
            socket = next((s for s in sockets if s.common_area_id == common_area.pk), None)
            device_specs.append(
                (
                    Ups,
                    {
                        "brand": "APC",
                        "model": "Smart-UPS 3000",
                        "serial": f"UP-{index:04d}",
                        "registration_code": f"REG-UP-{index:04d}",
                        "mac_address": f"00:1A:2B:{index + 50:02d}:CC:{index:02d}",
                        "usage_type": "serverRoom",
                        "space": None,
                        "common_area": common_area,
                        "socket": socket,
                        "capacity_va": 3000,
                    },
                )
            )

        # Switches
        for index, common_area in enumerate(common_areas[7:9], start=1):
            socket = next((s for s in sockets if s.common_area_id == common_area.pk), None)
            device_specs.append(
                (
                    Switch,
                    {
                        "brand": "Cisco",
                        "model": "Catalyst 9300",
                        "serial": f"SW-{index:04d}",
                        "registration_code": f"REG-SW-{index:04d}",
                        "mac_address": f"00:1A:2B:{index + 60:02d}:EE:{index:02d}",
                        "usage_type": "serverRoom",
                        "space": None,
                        "common_area": common_area,
                        "socket": socket,
                        "layer_capability": "L3",
                        "total_ports": 48,
                        "poe_supported": True,
                        "poe_budget_watts": 370,
                        "uplink_speed": "10 Gbps",
                        "downlink_speed": "1 Gbps",
                    },
                )
            )

        # Access Points
        for index, common_area in enumerate(common_areas[9:12], start=1):
            socket = next((s for s in sockets if s.common_area_id == common_area.pk), None)
            device_specs.append(
                (
                    AccessPoint,
                    {
                        "brand": "Ubiquiti",
                        "model": "U7 Pro",
                        "serial": f"AP-{index:04d}",
                        "registration_code": f"REG-AP-{index:04d}",
                        "mac_address": f"00:1A:2B:{index + 70:02d}:11:{index:02d}",
                        "usage_type": "office",
                        "space": None,
                        "common_area": common_area,
                        "socket": socket,
                        "gps_lat": 37.9752 + index * 0.01,
                        "gps_lon": 23.7348 + index * 0.01,
                    },
                )
            )

        # Phones
        for index, space in enumerate(spaces[15:20], start=1):
            socket = next((s for s in sockets if s.space_id == space.pk), None)
            device_specs.append(
                (
                    Phone,
                    {
                        "brand": "Yealink",
                        "model": "T54W",
                        "serial": f"PH-{index:04d}",
                        "registration_code": f"REG-PH-{index:04d}",
                        "mac_address": f"00:1A:2B:{index + 80:02d}:22:{index:02d}",
                        "usage_type": "office",
                        "space": space,
                        "common_area": None,
                        "socket": socket,
                        "phone_type": "digital",
                        "phone_number": 210000000 + index,
                    },
                )
            )

        reachable_test_ips = [
            "1.1.1.1",
            "1.0.0.1",
            "8.8.8.8",
            "8.8.4.4",
            "9.9.9.9",
            "149.112.112.112",
            "208.67.222.222",
            "208.67.220.220",
        ]
        next_unreachable_ip = 1
        for index, (_, payload) in enumerate(device_specs):
            if index < len(reachable_test_ips):
                payload["ip_address"] = reachable_test_ips[index]
            else:
                payload["ip_address"] = f"192.0.2.{next_unreachable_ip}"
                next_unreachable_ip += 1

        self.next_unreachable_ip = next_unreachable_ip

        devices = []
        for model_class, payload in device_specs:
            device = model_class(**payload)
            device.full_clean()
            device.save()
            devices.append(device)
        return devices

    def create_additional_network_devices(self, common_areas, sockets):
        created = []
        if not common_areas:
            return created

        ip_pool = [
            f"192.0.2.{self.next_unreachable_ip + offset}"
            for offset in range(15)
        ]
        self.next_unreachable_ip += len(ip_pool)

        for idx, common_area in enumerate(common_areas[:5], start=1):
            available_socket = next(
                (
                    s for s in sockets
                    if s.common_area_id == common_area.pk
                    and not Device.objects.filter(socket=s).exists()
                ),
                None,
            )

            if idx <= 5:
                server = ServerComputer(
                    brand="HPE",
                    model="ProLiant DL380 Gen10",
                    serial=f"SR-EX-{idx:03d}",
                    registration_code=f"REG-SR-EX-{idx:03d}",
                    ip_address=ip_pool[idx - 1],
                    mac_address=f"00:1B:44:{idx:02d}:AA:{idx:02d}",
                    usage_type="serverRoom",
                    space=None,
                    common_area=common_area,
                    socket=available_socket,
                    rack_unit="1U",
                )
                server.full_clean()
                server.save()
                created.append(server)

            switch = Switch(
                brand="Juniper",
                model="EX4300-48P",
                serial=f"SW-EX-{idx:03d}",
                registration_code=f"REG-SW-EX-{idx:03d}",
                ip_address=ip_pool[idx + 4],
                mac_address=f"00:1B:44:{idx + 10:02d}:BB:{idx:02d}",
                usage_type="serverRoom",
                space=None,
                common_area=common_area,
                socket=None,
                layer_capability="L3",
                total_ports=48,
                poe_supported=True,
                poe_budget_watts=370,
                uplink_speed="10 Gbps",
                downlink_speed="1 Gbps",
            )
            switch.full_clean()
            switch.save()
            created.append(switch)

            access_point = AccessPoint(
                brand="Aruba",
                model="AP-635",
                serial=f"AP-EX-{idx:03d}",
                registration_code=f"REG-AP-EX-{idx:03d}",
                ip_address=ip_pool[idx + 9],
                mac_address=f"00:1B:44:{idx + 20:02d}:CC:{idx:02d}",
                usage_type="office",
                space=None,
                common_area=common_area,
                socket=None,
                gps_lat=37.9752 + idx * 0.02,
                gps_lon=23.7348 + idx * 0.02,
            )
            access_point.full_clean()
            access_point.save()
            created.append(access_point)

        return created

    def create_peripherals(self, devices):
        peripheral_counter = 1
        for device in devices:
            peripheral_types = [
                ("monitor", "Dell", "P2422H", "24-inch IPS display"),
                ("keyboard", "Logitech", "K380", "Wireless keyboard"),
                ("mouse", "Logitech", "M185", "USB mouse"),
            ]

            for peripheral_type, brand, model, spec in peripheral_types[:2]:
                peripheral = Peripheral(
                    device=device,
                    peripheral_type=peripheral_type,
                    brand=brand,
                    model=model,
                    serial_number=f"PER-{peripheral_counter:05d}",
                    specifications=spec,
                    valid_from=date(2021, 1, 1),
                    valid_to=None,
                    is_active=True,
                )
                peripheral.full_clean()
                peripheral.save()
                peripheral_counter += 1

    def create_assignments(self, users, devices):
        assignments = []

        # Primary assignments for the first devices
        for idx, device in enumerate(devices[:8]):
            user = users[idx % len(users)]
            assignment = Assignment(
                user=user,
                device=device,
                assignment_date=date(2023, 1, 15) + timedelta(days=idx * 7),
                end_date=None,
                assignment_type="primary",
                notes="Primary workstation assignment",
            )
            assignment.full_clean()
            assignment.save()
            assignments.append(assignment)

        # Shared assignment pattern for a couple of devices
        shared_device = devices[8]
        for offset, user in enumerate(users[:2]):
            assignment = Assignment(
                user=user,
                device=shared_device,
                assignment_date=date(2024, 2, 1) + timedelta(days=offset * 10),
                end_date=date(2024, 5, 31) + timedelta(days=offset * 10),
                assignment_type="shared",
                notes="Shared hotdesk assignment",
            )
            assignment.full_clean()
            assignment.save()
            assignments.append(assignment)

        # Temporary assignment for another device
        temp_device = devices[9]
        temp_user = users[2]
        assignment = Assignment(
            user=temp_user,
            device=temp_device,
            assignment_date=date(2024, 6, 1),
            end_date=date(2024, 7, 15),
            assignment_type="temporary",
            notes="Temporary assignment during leave coverage",
        )
        assignment.full_clean()
        assignment.save()
        assignments.append(assignment)

        # Assign each phone to a user so phone-book rows have realistic data.
        phones = [device for device in devices if isinstance(device, Phone)]
        for idx, phone in enumerate(phones):
            user = users[idx + 8]
            assignment = Assignment(
                user=user,
                device=phone,
                assignment_date=date.today(),
                end_date=None,
                assignment_type="primary",
                notes="Assigned desk phone",
            )
            assignment.full_clean()
            assignment.save()
            assignments.append(assignment)

        return assignments
