from datetime import date

from django.core.exceptions import ValidationError
from django.core.management import get_commands
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import City
from .views import get_search_result_url


class AreasBreadcrumbTests(TestCase):
    def test_areas_page_has_a_current_breadcrumb(self):
        response = self.client.get(reverse('areas-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_title'], 'Areas')
        self.assertContains(response, '<span>Areas</span>', html=False)
        self.assertContains(response, 'nav-item dropdown border border-primary-subtle rounded-3')
        self.assertContains(response, 'nav-item dropdown border border-primary-subtle rounded-3 bg-secondary')
        self.assertContains(response, 'nav-link dropdown-toggle px-3 py-2 fw-medium')


class FloorCreateRedirectTests(TestCase):
    def test_creating_floor_returns_to_floors_list(self):
        from .models import Area, Building, City, Floor

        city = City.objects.create(name='Athens')
        area = Area.objects.create(name='Central', city=city)
        building = Building.objects.create(name='Main', area=area)

        response = self.client.post(reverse('new-floor'), {
            'floor_number': 2,
            'building': building.pk,
            'is_active': True,
            'valid_from': date.today().isoformat(),
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('floors-list'))
        self.assertTrue(Floor.objects.filter(building=building, floor_number=2).exists())


class DeviceSocketLocationTests(TestCase):
    def setUp(self):
        from .models import Area, Building, City, CommonArea, Floor, Room, Socket, Space

        city = City.objects.create(name='Athens')
        area = Area.objects.create(name='Central', city=city)
        building = Building.objects.create(name='Main', area=area)
        floor = Floor.objects.create(building=building, floor_number=1)
        room = Room.objects.create(floor=floor, room_code='A101')
        self.space = Space.objects.create(room=room, name='Desk 1')
        self.other_space = Space.objects.create(room=room, name='Desk 2')
        self.common_area = CommonArea.objects.create(floor=floor, name='Corridor')
        self.other_common_area = CommonArea.objects.create(floor=floor, name='Lobby')
        Socket.objects.create(socket_code='SPACE-1', building=building, space=self.space)
        Socket.objects.create(socket_code='AREA-1', building=building, common_area=self.common_area)

    def test_socket_options_include_their_location_ids(self):
        from .forms import DesktopForm

        socket_options = str(DesktopForm()['socket'])

        self.assertIn(f'data-space-id="{self.space.pk}"', socket_options)
        self.assertIn(f'data-common-area-id="{self.common_area.pk}"', socket_options)

    def test_device_rejects_socket_from_a_different_location(self):
        from .models import Device, Socket

        mismatched_pairs = [
            (self.space, None, Socket.objects.get(socket_code='AREA-1')),
            (None, self.common_area, Socket.objects.get(socket_code='SPACE-1')),
        ]
        for index, (space, common_area, socket) in enumerate(mismatched_pairs):
            with self.subTest(socket=socket.socket_code):
                device = Device(
                    brand='Test',
                    serial=f'SOCKET-LOCATION-{index}',
                    usage_type='office',
                    space=space,
                    common_area=common_area,
                    socket=socket,
                )
                with self.assertRaises(ValidationError) as raised:
                    device.clean()
                self.assertIn('socket', raised.exception.message_dict)


class StatisticsDrilldownTests(TestCase):
    def test_statistics_charts_link_to_filtered_pages_and_omit_active_assignments(self):
        response = self.client.get(reverse('device-statistics'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('desktops-list'))
        self.assertContains(response, reverse('areas-list'))
        self.assertContains(response, reverse('ping-all-devices') + '?status=failed')
        self.assertContains(response, reverse('devices-list') + '?assignment_status=assigned')
        self.assertContains(response, reverse('ping-all-devices') + '?status=reachable')
        self.assertNotContains(response, 'Active assignments')

        export_response = self.client.get(reverse('export-device-statistics', kwargs={'format_name': 'json'}))
        self.assertEqual(export_response.status_code, 200)
        self.assertNotIn('active_assignments', export_response.content.decode('utf-8'))

    def test_devices_list_filters_by_assignment_status(self):
        from .models import Assignment, Device, User

        user = User.objects.create(name='Alex', surname='Example', email='stats-user@example.com')
        assigned_device = Device.objects.create(
            brand='Assigned', serial='STATS-ASSIGNED-01', usage_type='office'
        )
        unassigned_device = Device.objects.create(
            brand='Unassigned', serial='STATS-UNASSIGNED-01', usage_type='office'
        )
        Assignment.objects.create(user=user, device=assigned_device, assignment_date=date.today())

        assigned_response = self.client.get(
            reverse('devices-list'), {'assignment_status': 'assigned'}
        )
        unassigned_response = self.client.get(
            reverse('devices-list'), {'assignment_status': 'unassigned'}
        )

        self.assertContains(assigned_response, 'STATS-ASSIGNED-01')
        self.assertContains(assigned_response, 'Assigned User')
        self.assertContains(assigned_response, 'Alex Example')
        self.assertNotContains(assigned_response, 'STATS-UNASSIGNED-01')
        self.assertContains(unassigned_response, 'Unassigned')
        self.assertNotContains(unassigned_response, 'Assigned User')
        self.assertContains(unassigned_response, 'STATS-UNASSIGNED-01')
        self.assertNotContains(unassigned_response, 'STATS-ASSIGNED-01')

    def test_ping_results_filter_to_reachable_devices(self):
        from unittest.mock import patch
        from .models import Device

        reachable_device = Device.objects.create(
            brand='Reachable', serial='STATS-PING-REACHABLE', usage_type='office', ip_address='192.0.2.10'
        )
        Device.objects.create(
            brand='Failed', serial='STATS-PING-FAILED', usage_type='office', ip_address='192.0.2.11'
        )
        ping_results = {
            '192.0.2.10': (True, 'Reply received'),
            '192.0.2.11': (False, 'Request timed out'),
        }

        with patch('nodes.views._run_ping', side_effect=lambda ip: ping_results[ip]):
            response = self.client.get(reverse('ping-all-devices'), {'status': 'reachable'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reachable devices')
        self.assertContains(response, reachable_device.serial)
        self.assertNotContains(response, 'STATS-PING-FAILED')

    def test_single_ping_displays_successful_reachability_in_result_row(self):
        from unittest.mock import patch

        with patch('nodes.views._run_ping', return_value=(True, 'Reply received')):
            response = self.client.get(reverse('ping_device'), {'ip': '192.0.2.10'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['reachable'])
        self.assertContains(response, 'Reachable')
        self.assertContains(response, 'Reply received')
        self.assertNotContains(response, 'No output returned.')
        self.assertNotContains(response, '>Failed</span>')


class ExportRouteTests(TestCase):
    def test_export_json_route_returns_json(self):
        City.objects.create(name="Athens")

        response = self.client.get(reverse("export-records", kwargs={"model_name": "city", "format_name": "json"}))

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response["Content-Type"])
        self.assertIn("Athens", response.content.decode("utf-8"))

    def test_export_docx_route_returns_docx(self):
        City.objects.create(name="Thessaloniki")

        response = self.client.get(reverse("export-records", kwargs={"model_name": "city", "format_name": "docx"}))

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.wordprocessingml.document", response["Content-Type"])

    def test_detail_page_exports_selected_record(self):
        city = City.objects.create(name="Athens")
        City.objects.create(name="Patras")

        detail_response = self.client.get(reverse("city-detail", kwargs={"pk": city.pk}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, f"/export/city/{city.pk}/json/")

        export_response = self.client.get(reverse("export-record", kwargs={
            "model_name": "city",
            "pk": city.pk,
            "format_name": "json",
        }))
        csv_content = export_response.content.decode("utf-8")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("Athens", csv_content)
        self.assertIn("Desktop Workstations", csv_content)
        self.assertNotIn("Patras", csv_content)


class WorkstationListTests(TestCase):
    def test_combined_workstations_list_renders_all_pc_assignments(self):
        from .models import (
            AllInOneComputer, Area, Assignment, Building, City, Department,
            DesktopComputer, Directorate, Floor, GeneralDirectorate, LaptopComputer,
            Office, Room, Space, User,
        )

        general_directorate = GeneralDirectorate.objects.create(name="IT")
        directorate = Directorate.objects.create(name="Operations", general_directorate=general_directorate)
        department = Department.objects.create(name="Support", directorate=directorate)
        office = Office.objects.create(name="Support Office", department=department)
        user = User.objects.create(
            name="Alex",
            surname="Androulakis",
            email="alex@example.com",
            general_directorate=general_directorate,
            directorate=directorate,
            department=department,
            office=office,
        )
        second_user = User.objects.create(
            name="Maria",
            surname="Papadopoulou",
            email="maria@example.com",
            general_directorate=general_directorate,
            directorate=directorate,
            department=department,
            office=office,
        )

        city = City.objects.create(name="Athens")
        area = Area.objects.create(name="HQ", city=city)
        building = Building.objects.create(name="Main", area=area)
        floor = Floor.objects.create(building=building, floor_number=1)
        room = Room.objects.create(floor=floor, room_code="A101")
        space = Space.objects.create(room=room, name="Desk 1")

        desktop = DesktopComputer.objects.create(
            brand="Dell",
            model="OptiPlex",
            serial="CPU-1001",
            registration_code="REG-1001",
            ip_address="10.0.0.10",
            mac_address="00:11:22:33:44:11",
            usage_type="office",
            space=space,
            cpu="i7",
            ram_gb=16,
            storage_gb=512,
        )
        AllInOneComputer.objects.create(
            brand="Lenovo",
            model="IdeaCentre",
            serial="AIO-1001",
            registration_code="REG-AIO-1001",
            ip_address="10.0.0.11",
            mac_address="00:11:22:33:44:12",
            usage_type="office",
            space=space,
            cpu="i5",
            ram_gb=8,
            storage_gb=256,
            screen_size=24,
        )
        LaptopComputer.objects.create(
            brand="HP",
            model="EliteBook",
            serial="LAP-1001",
            registration_code="REG-LAP-1001",
            ip_address="10.0.0.12",
            mac_address="00:11:22:33:44:13",
            usage_type="office",
            space=space,
            cpu="i7",
            ram_gb=16,
            storage_gb=512,
            screen_size=14,
        )

        Assignment.objects.create(user=user, device=desktop, assignment_date=date.today(), assignment_type='primary')
        Assignment.objects.create(user=second_user, device=desktop, assignment_date=date.today(), assignment_type='shared')

        response = self.client.get(reverse("workstations-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All PCs")
        self.assertContains(response, "Manage All PCs")
        self.assertContains(response, "Device")
        self.assertContains(response, "Registration")
        self.assertContains(response, "Assigned User")
        self.assertContains(response, "Alex")
        self.assertContains(response, "Maria")
        self.assertContains(response, "Dell")
        self.assertContains(response, "Lenovo")
        self.assertContains(response, "HP")


class PhoneBookTests(TestCase):
    def test_phone_book_shows_active_phone_assignments_and_users_without_phones(self):
        from .models import (
            Area, Assignment, Building, City, CommonArea, Floor, Phone, Room, Socket,
            Space, User,
        )

        user = User.objects.create(
            name="Alex",
            surname="Androulakis",
            email="alex-phonebook@example.com",
            phone="2100001",
        )
        user_without_phone = User.objects.create(
            name="Maria",
            surname="Papadopoulou",
            email="maria-phonebook@example.com",
        )
        user_without_number = User.objects.create(
            name="Nikos",
            surname="Georgiou",
            email="nikos-phonebook@example.com",
        )
        user_with_common_area_phone = User.objects.create(
            name="Eleni",
            surname="Dimitriou",
            email="eleni-phonebook@example.com",
        )
        city = City.objects.create(name="Athens")
        area = Area.objects.create(name="HQ", city=city)
        building = Building.objects.create(name="Main", area=area)
        floor = Floor.objects.create(building=building, floor_number=2)
        common_area = CommonArea.objects.create(floor=floor, name="Lobby")
        room = Room.objects.create(floor=floor, room_code="B204")
        space = Space.objects.create(room=room, name="Reception")
        socket = Socket.objects.create(
            socket_code="SOCKET-B204-01",
            space=space,
            building=building,
        )
        phone = Phone.objects.create(
            brand="Cisco",
            model="Desk Phone",
            serial="PHONE-1001",
            registration_code="REG-PHONE-1001",
            usage_type="office",
            phone_type="digital",
            phone_number=5551001,
            space=space,
            socket=socket,
        )
        Assignment.objects.create(
            user=user,
            device=phone,
            assignment_date=date.today(),
        )
        phone_without_number = Phone.objects.create(
            brand="Cisco",
            model="Desk Phone",
            serial="PHONE-1002",
            registration_code="REG-PHONE-1002",
            usage_type="office",
            phone_type="digital",
            space=space,
        )
        Assignment.objects.create(
            user=user_without_number,
            device=phone_without_number,
            assignment_date=date.today(),
        )
        common_area_phone = Phone.objects.create(
            brand="Cisco",
            model="Desk Phone",
            serial="PHONE-1003",
            registration_code="REG-PHONE-1003",
            usage_type="office",
            phone_type="digital",
            phone_number=5551003,
            common_area=common_area,
        )
        Assignment.objects.create(
            user=user_with_common_area_phone,
            device=common_area_phone,
            assignment_date=date.today(),
        )

        response = self.client.get(reverse("phone-book"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alex Androulakis")
        self.assertContains(response, "alex-phonebook@example.com")
        self.assertContains(response, "5551001")
        self.assertContains(response, "Personal Phone")
        self.assertContains(response, "2100001")
        self.assertContains(response, "SOCKET-B204-01")
        self.assertContains(response, "Main - Floor 2 - B204 - Reception")
        self.assertContains(response, "Main - Floor 2 - Lobby")
        self.assertNotContains(response, "Athens / Hq / Main")
        self.assertContains(response, "Nikos Georgiou")
        self.assertContains(response, "No number listed")
        self.assertContains(response, "Maria Papadopoulou")
        self.assertContains(response, "No phone assigned")


class UserContactDisplayTests(TestCase):
    def test_users_list_and_detail_show_full_name_and_both_phone_numbers(self):
        from .models import Assignment, Phone, User

        user = User.objects.create(
            name='Alex',
            surname='Androulakis',
            email='alex-user-contact@example.com',
            phone='2101111',
        )
        phone = Phone.objects.create(
            brand='Cisco',
            model='Desk Phone',
            serial='USER-CONTACT-PHONE-01',
            registration_code='USER-CONTACT-REG-01',
            usage_type='office',
            phone_type='digital',
            phone_number=2102222,
        )
        Assignment.objects.create(
            user=user,
            device=phone,
            assignment_date=date.today(),
        )

        list_response = self.client.get(reverse('users-list'))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, 'Full Name')
        self.assertContains(list_response, 'Alex Androulakis')
        self.assertContains(list_response, 'Personal Phone')
        self.assertContains(list_response, '2101111')
        self.assertContains(list_response, 'Assigned Phone')
        self.assertContains(list_response, '2102222')

        detail_response = self.client.get(reverse('user-detail', kwargs={'pk': user.pk}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Full Name')
        self.assertContains(detail_response, 'Personal Phone')
        self.assertContains(detail_response, 'Assigned phone number:')
        self.assertContains(detail_response, '2102222')


class PingDeviceTests(TestCase):
    def test_ping_view_accepts_ip_address_parameter_for_active_device(self):
        from .models import Area, Building, City, DesktopComputer, Floor, Room, Space

        city = City.objects.create(name="Athens")
        area = Area.objects.create(name="HQ", city=city)
        building = Building.objects.create(name="Main", area=area)
        floor = Floor.objects.create(building=building, floor_number=1)
        room = Room.objects.create(floor=floor, room_code="A101")
        space = Space.objects.create(room=room, name="Desk 1")
        device = DesktopComputer.objects.create(
            brand="Dell",
            model="OptiPlex",
            serial="DN-1001",
            registration_code="REG-1001",
            ip_address="10.0.0.77",
            mac_address="00:11:22:33:44:55",
            usage_type="office",
            space=space,
            cpu="i7",
            ram_gb=16,
            storage_gb=512,
        )

        response = self.client.get(reverse("ping_device"), {
            "ip_address": "10.0.0.77",
            "return_url": f"/desktops/{device.pk}/",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "10.0.0.77")
        self.assertContains(response, f'href="/desktops/{device.pk}/"')
        self.assertNotContains(response, "No IP address was provided")


class MaterialHandoverTests(TestCase):
    def test_material_handover_form_renders(self):
        response = self.client.get(reverse("material-handover"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Material Charge Details")
        self.assertContains(response, "Material Handover")
        self.assertContains(response, "Select device")

    def test_user_options_include_only_assigned_users(self):
        from .forms import MaterialHandoverForm
        from .models import (
            Area, Assignment, Building, City, Department, DesktopComputer,
            Directorate, Floor, GeneralDirectorate, Office, Room, Space, User,
        )

        general_directorate = GeneralDirectorate.objects.create(name="IT")
        directorate = Directorate.objects.create(name="Operations", general_directorate=general_directorate)
        department = Department.objects.create(name="Support", directorate=directorate)
        office = Office.objects.create(name="Support Office", department=department)

        assigned_user = User.objects.create(
            name="Alex",
            surname="Androulakis",
            email="alex@example.com",
            general_directorate=general_directorate,
            directorate=directorate,
            department=department,
            office=office,
        )
        unassigned_user = User.objects.create(
            name="Nina",
            surname="Petrou",
            email="nina@example.com",
            general_directorate=general_directorate,
            directorate=directorate,
            department=department,
            office=office,
        )

        city = City.objects.create(name="Athens")
        area = Area.objects.create(name="HQ", city=city)
        building = Building.objects.create(name="Main", area=area)
        floor = Floor.objects.create(building=building, floor_number=1)
        room = Room.objects.create(floor=floor, room_code="A101")
        space = Space.objects.create(room=room, name="Desk 1")
        device = DesktopComputer.objects.create(
            brand="Dell",
            model="OptiPlex",
            serial="CPU-1001",
            registration_code="REG-1001",
            ip_address="10.0.0.20",
            mac_address="00:11:22:33:44:66",
            usage_type="office",
            space=space,
            cpu="i7",
            ram_gb=16,
            storage_gb=512,
        )
        Assignment.objects.create(
            user=assigned_user,
            device=device,
            assignment_date=date.today(),
            assignment_type='primary',
        )

        queryset = MaterialHandoverForm().fields["users"].queryset

        self.assertIn(assigned_user, queryset)
        self.assertNotIn(unassigned_user, queryset)

    def test_user_selection_uses_assigned_devices_without_manual_device_choice(self):
        from .forms import MaterialHandoverForm
        from .models import (
            Area, Assignment, Building, City, Department, DesktopComputer,
            Directorate, Floor, GeneralDirectorate, Office, Room, Space, User,
        )

        general_directorate = GeneralDirectorate.objects.create(name="IT")
        directorate = Directorate.objects.create(name="Operations", general_directorate=general_directorate)
        department = Department.objects.create(name="Support", directorate=directorate)
        office = Office.objects.create(name="Support Office", department=department)
        user = User.objects.create(
            name="Alex",
            surname="Androulakis",
            email="alex@example.com",
            general_directorate=general_directorate,
            directorate=directorate,
            department=department,
            office=office,
        )

        city = City.objects.create(name="Athens")
        area = Area.objects.create(name="HQ", city=city)
        building = Building.objects.create(name="Main", area=area)
        floor = Floor.objects.create(building=building, floor_number=1)
        room = Room.objects.create(floor=floor, room_code="A101")
        space = Space.objects.create(room=room, name="Desk 1")
        device = DesktopComputer.objects.create(
            brand="Dell",
            model="OptiPlex",
            serial="CPU-2001",
            registration_code="REG-2001",
            ip_address="10.0.0.21",
            mac_address="00:11:22:33:44:77",
            usage_type="office",
            space=space,
            cpu="i7",
            ram_gb=16,
            storage_gb=512,
        )
        Assignment.objects.create(
            user=user,
            device=device,
            assignment_date=date.today(),
            assignment_type='primary',
        )

        form = MaterialHandoverForm(data={
            'users': [user.pk],
            'report_date': date.today(),
            'comments': 'Test',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data['selected_devices']), 1)
        self.assertEqual(form.cleaned_data['selected_devices'][0].pk, device.pk)

    def test_selected_users_must_share_the_same_assigned_device(self):
        from .forms import MaterialHandoverForm
        from .models import (
            Area, Assignment, Building, City, Department, DesktopComputer,
            Directorate, Floor, GeneralDirectorate, Office, Room, Space, User,
        )

        general_directorate = GeneralDirectorate.objects.create(name="IT")
        directorate = Directorate.objects.create(name="Operations", general_directorate=general_directorate)
        department = Department.objects.create(name="Support", directorate=directorate)
        office = Office.objects.create(name="Support Office", department=department)

        user_one = User.objects.create(
            name="Alex",
            surname="Androulakis",
            email="alex@example.com",
            general_directorate=general_directorate,
            directorate=directorate,
            department=department,
            office=office,
        )
        user_two = User.objects.create(
            name="Nina",
            surname="Petrou",
            email="nina@example.com",
            general_directorate=general_directorate,
            directorate=directorate,
            department=department,
            office=office,
        )

        city = City.objects.create(name="Athens")
        area = Area.objects.create(name="HQ", city=city)
        building = Building.objects.create(name="Main", area=area)
        floor = Floor.objects.create(building=building, floor_number=1)
        room = Room.objects.create(floor=floor, room_code="A101")
        space = Space.objects.create(room=room, name="Desk 1")

        device_one = DesktopComputer.objects.create(
            brand="Dell",
            model="OptiPlex",
            serial="CPU-5001",
            registration_code="REG-5001",
            ip_address="10.0.0.51",
            mac_address="00:11:22:33:44:11",
            usage_type="office",
            space=space,
            cpu="i7",
            ram_gb=16,
            storage_gb=512,
        )
        device_two = DesktopComputer.objects.create(
            brand="Lenovo",
            model="ThinkCentre",
            serial="CPU-5002",
            registration_code="REG-5002",
            ip_address="10.0.0.52",
            mac_address="00:11:22:33:44:22",
            usage_type="office",
            space=space,
            cpu="i5",
            ram_gb=8,
            storage_gb=256,
        )

        Assignment.objects.create(user=user_one, device=device_one, assignment_date=date.today(), assignment_type='primary')
        Assignment.objects.create(user=user_two, device=device_two, assignment_date=date.today(), assignment_type='primary')

        form = MaterialHandoverForm(data={
            'users': [user_one.pk, user_two.pk],
            'report_date': date.today(),
            'comments': 'Test',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('must share the same assigned device', str(form.errors['__all__']))

    def test_user_options_include_unique_context(self):
        from .forms import MaterialHandoverForm
        from .models import Department, GeneralDirectorate, Directorate, Office, User

        general_directorate = GeneralDirectorate.objects.create(name="IT")
        directorate = Directorate.objects.create(name="Operations", general_directorate=general_directorate)
        department = Department.objects.create(name="Support", directorate=directorate)
        office = Office.objects.create(name="Support Office", department=department)
        user = User.objects.create(
            name="Alex",
            surname="Androulakis",
            email="alex@example.com",
            general_directorate=general_directorate,
            directorate=directorate,
            department=department,
            office=office,
        )

        option = MaterialHandoverForm().fields["users"].label_from_instance(user)

        self.assertIn("Alex Androulakis", option)
        self.assertIn("It", option)
        self.assertIn("Support", option)
        self.assertNotIn("Support Office", option)
        self.assertNotIn("alex@example.com", option)


class WatsonBuildIndexCommandTests(SimpleTestCase):
    def test_watson_build_index_command_is_registered(self):
        self.assertIn("watson_build_index", get_commands())


class SearchResultUrlTests(SimpleTestCase):
    def test_get_search_result_url_returns_city_detail_route(self):
        class CityStub:
            pk = 7
            _meta = type("Meta", (), {"app_label": "nodes", "model_name": "city"})()

        city = CityStub()

        self.assertEqual(get_search_result_url(city), reverse("city-detail", kwargs={"pk": city.pk}))


class AssignmentAndHandoverPeripheralTests(TestCase):
    def test_user_detail_assignment_links_to_specific_device_page(self):
        from .models import Area, Assignment, Building, City, DesktopComputer, Floor, Room, Space, User

        user = User.objects.create(name="Alex", surname="Example", email="alex-user-detail@example.com")
        city = City.objects.create(name="Athens")
        area = Area.objects.create(name="HQ", city=city)
        building = Building.objects.create(name="Main", area=area)
        floor = Floor.objects.create(building=building, floor_number=1)
        room = Room.objects.create(floor=floor, room_code="U101")
        space = Space.objects.create(room=room, name="Desk")
        device = DesktopComputer.objects.create(
            brand="Dell",
            serial="USER-DETAIL-CPU-01",
            usage_type="office",
            space=space,
            cpu="i7",
            ram_gb=16,
            storage_gb=512,
        )
        Assignment.objects.create(user=user, device=device, assignment_date=date.today())

        response = self.client.get(reverse('user-detail', kwargs={'pk': user.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("desktop-detail", kwargs={"pk": device.pk})}"',
        )

    def test_assignment_detail_page_shows_peripherals(self):
        from .models import (
            Area, Assignment, Building, City, Department, DesktopComputer,
            Directorate, Floor, GeneralDirectorate, Office, Peripheral, Room, Space, User,
        )

        general_directorate = GeneralDirectorate.objects.create(name="IT")
        directorate = Directorate.objects.create(name="Operations", general_directorate=general_directorate)
        department = Department.objects.create(name="Support", directorate=directorate)
        office = Office.objects.create(name="Support Office", department=department)
        user = User.objects.create(
            name="Alex",
            surname="Androulakis",
            email="alex@example.com",
            general_directorate=general_directorate,
            directorate=directorate,
            department=department,
            office=office,
        )
        city = City.objects.create(name="Athens")
        area = Area.objects.create(name="HQ", city=city)
        building = Building.objects.create(name="Main", area=area)
        floor = Floor.objects.create(building=building, floor_number=1)
        room = Room.objects.create(floor=floor, room_code="A101")
        space = Space.objects.create(room=room, name="Desk 1")
        device = DesktopComputer.objects.create(
            brand="Dell",
            model="OptiPlex",
            serial="CPU-3001",
            registration_code="REG-3001",
            ip_address="10.0.0.30",
            mac_address="00:11:22:33:44:88",
            usage_type="office",
            space=space,
            cpu="i7",
            ram_gb=16,
            storage_gb=512,
        )
        peripheral = Peripheral.objects.create(
            device=device,
            peripheral_type='keyboard',
            brand='Logitech',
            model='K120',
            serial_number='PER-3001',
            specifications='USB',
        )
        assignment = Assignment.objects.create(
            user=user,
            device=device,
            assignment_date=date.today(),
            assignment_type='primary',
        )
        second_device = DesktopComputer.objects.create(
            brand="Lenovo",
            model="ThinkCentre",
            serial="CPU-3002",
            registration_code="REG-3002",
            ip_address="10.0.0.31",
            mac_address="00:11:22:33:44:89",
            usage_type="office",
            space=space,
            cpu="i5",
            ram_gb=8,
            storage_gb=256,
        )
        overlapping_primary = Assignment(
            user=user,
            device=second_device,
            assignment_date=date.today(),
            assignment_type='primary',
        )
        overlapping_primary.full_clean()
        overlapping_primary.save()

        response = self.client.get(reverse('assignment-detail', kwargs={'pk': assignment.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Attached Peripherals')
        self.assertContains(response, 'PER-3001')
        self.assertContains(response, 'CPU-3001')
        self.assertContains(response, 'CPU-3002')
        self.assertContains(response, 'nav nav-tabs w-100 border-0 mb-0')
        self.assertContains(response, 'active bg-secondary-subtle text-dark border-0')
        self.assertContains(response, 'w-100 border-top border-2 rounded-pill')
        self.assertContains(response, 'border-top-color: var(--bs-secondary-bg-subtle) !important;')

        assignments_response = self.client.get(reverse('assignments-list'))

        self.assertEqual(assignments_response.status_code, 200)
        self.assertContains(assignments_response, 'Alex Androulakis')
        self.assertEqual(assignments_response.content.count(b'<tr class="border-bottom">'), 1)

    def test_material_handover_report_includes_peripherals_as_items(self):
        from .forms import MaterialHandoverForm
        from .models import (
            Area, Assignment, Building, City, Department, DesktopComputer,
            Directorate, Floor, GeneralDirectorate, Office, Peripheral, Room, Space, User,
        )

        general_directorate = GeneralDirectorate.objects.create(name="IT")
        directorate = Directorate.objects.create(name="Operations", general_directorate=general_directorate)
        department = Department.objects.create(name="Support", directorate=directorate)
        office = Office.objects.create(name="Support Office", department=department)
        user = User.objects.create(
            name="Alex",
            surname="Androulakis",
            email="alex@example.com",
            general_directorate=general_directorate,
            directorate=directorate,
            department=department,
            office=office,
        )
        city = City.objects.create(name="Athens")
        area = Area.objects.create(name="HQ", city=city)
        building = Building.objects.create(name="Main", area=area)
        floor = Floor.objects.create(building=building, floor_number=1)
        room = Room.objects.create(floor=floor, room_code="A101")
        space = Space.objects.create(room=room, name="Desk 1")
        device = DesktopComputer.objects.create(
            brand="Dell",
            model="OptiPlex",
            serial="CPU-4001",
            registration_code="REG-4001",
            ip_address="10.0.0.40",
            mac_address="00:11:22:33:44:99",
            usage_type="office",
            space=space,
            cpu="i7",
            ram_gb=16,
            storage_gb=512,
        )
        peripheral = Peripheral.objects.create(
            device=device,
            peripheral_type='mouse',
            brand='Logitech',
            model='M185',
            serial_number='PER-4001',
            specifications='Wireless',
        )
        Assignment.objects.create(
            user=user,
            device=device,
            assignment_date=date.today(),
            assignment_type='primary',
        )

        form = MaterialHandoverForm(data={
            'users': [user.pk],
            'report_date': date.today(),
            'comments': 'Test',
        })
        self.assertTrue(form.is_valid(), form.errors)

        response = self.client.post(reverse('material-handover'), {
            'users': [user.pk],
            'report_date': date.today(),
            'comments': 'Test',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PER-4001')


class PeripheralDetailPageTests(TestCase):
    def test_peripheral_detail_shows_connected_device(self):
        from .models import (
            Area, Building, City, DesktopComputer, Floor, Peripheral, Room, Space,
        )

        city = City.objects.create(name="Athens")
        area = Area.objects.create(name="IT", city=city)
        building = Building.objects.create(name="Main Building", area=area)
        floor = Floor.objects.create(building=building, floor_number=1)
        room = Room.objects.create(floor=floor, room_code="A101")
        space = Space.objects.create(room=room, name="Desk 1")
        device = DesktopComputer.objects.create(
            brand="Dell",
            model="OptiPlex",
            serial="DEV-1001",
            registration_code="REG-1001",
            ip_address="10.0.0.10",
            mac_address="00:11:22:33:44:55",
            usage_type="office",
            space=space,
            cpu="i7",
            ram_gb=16,
            storage_gb=512,
        )
        peripheral = Peripheral.objects.create(
            device=device,
            peripheral_type="keyboard",
            brand="Logitech",
            model="K120",
            serial_number="PER-1001",
            specifications="USB wired",
        )

        response = self.client.get(reverse("peripheral-detail", kwargs={"pk": peripheral.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connected Device")
        self.assertContains(response, "Dell")
        self.assertContains(response, "DEV-1001")
