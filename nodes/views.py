from django.apps import apps
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.urls import resolve, reverse
from django.test import RequestFactory
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Prefetch, Q, F, ExpressionWrapper, IntegerField, Count
import html
import io
import json
import re
import zipfile
import struct
import zlib
import math
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie
from html.parser import HTMLParser

from .forms import *
from . models import *

from .view_helpers import handle_create, handle_update, handle_delete
from .forms import MaterialHandoverForm
import subprocess
import platform
from concurrent.futures import ThreadPoolExecutor


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def dashboard(request):
    # Dashboard totals.
    context = {
        "general_directorates_count": GeneralDirectorate.objects.count(),
        "directorates_count":         Directorate.objects.count(),
        "departments_count":          Department.objects.count(),
        "offices_count":              Office.objects.count(),
        "cities_count":               City.objects.count(),
        "areas_count":                Area.objects.count(),
        "buildings_count":            Building.objects.count(),
        "floors_count":               Floor.objects.count(),
        "rooms_count":                Room.objects.count(),
        "common_areas_count":         CommonArea.objects.count(),
        "spaces_count":               Space.objects.count(),
        "sockets_count":              Socket.objects.count(),
        "assignments_count":          Assignment.objects.count(),
        "users_count":                User.objects.count(),
        "devices_count":              Device.objects.count(),
        "peripherals_count":          Peripheral.objects.count(),
        "desktops_count":             DesktopComputer.objects.count(),
        "laptops_count":              LaptopComputer.objects.count(),
        "servers_count":              ServerComputer.objects.count(),
        "allInOnes_count":            AllInOneComputer.objects.count(),
        "printers_count":             Printer.objects.count(),
        "switches_count":             Switch.objects.count(),
        "access_points_count":        AccessPoint.objects.count(),
        "upses_count":                Ups.objects.count(),
        "phones_count":               Phone.objects.count(),
    }
    return render(request, "inventory/dashboard.html", context)


def device_statistics(request):
    active_assignments = Assignment.objects.filter(
        Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate())
    )
    total_devices = Device.objects.count()
    assigned_devices = active_assignments.values('device_id').distinct().count()
    pingable_ips = list(
        Device.objects.exclude(ip_address__isnull=True)
        .exclude(ip_address='')
        .values_list('ip_address', flat=True)
    )
    ping_worker_count = min(32, max(1, len(pingable_ips)))
    with ThreadPoolExecutor(max_workers=ping_worker_count) as executor:
        ping_statuses = list(executor.map(_run_ping, pingable_ips))
    reachable_count = sum(status[0] for status in ping_statuses)
    unreachable_count = len(ping_statuses) - reachable_count

    statistics_sections = [
        ('Spatial inventory', 'bi-geo-alt', [
            ('Cities', City.objects.count(), 'bi-geo-alt'),
            ('Areas', Area.objects.count(), 'bi-map'),
            ('Buildings', Building.objects.count(), 'bi-building'),
            ('Floors', Floor.objects.count(), 'bi-layers'),
            ('Rooms', Room.objects.count(), 'bi-door-open'),
            ('Spaces', Space.objects.count(), 'bi-grid-3x3-gap'),
            ('Common areas', CommonArea.objects.count(), 'bi-grid'),
            ('Sockets', Socket.objects.count(), 'bi-ethernet'),
        ]),
        ('Organization', 'bi-diagram-3', [
            ('General directorates', GeneralDirectorate.objects.count(), 'bi-diagram-3'),
            ('Directorates', Directorate.objects.count(), 'bi-diagram-2'),
            ('Departments', Department.objects.count(), 'bi-diagram-3'),
            ('Offices', Office.objects.count(), 'bi-briefcase'),
            ('Users', User.objects.count(), 'bi-people'),
        ]),
        ('Assignments and inventory', 'bi-clipboard-data', [
            ('Assignments', Assignment.objects.count(), 'bi-clipboard-check'),
            ('Peripherals', Peripheral.objects.count(), 'bi-usb-symbol'),
            ('All devices', total_devices, 'bi-hdd-stack'),
        ]),
        ('Devices by type', 'bi-bar-chart-line', [
            ('Desktops', DesktopComputer.objects.count(), 'bi-pc-display'),
            ('All-In-Ones', AllInOneComputer.objects.count(), 'bi-display'),
            ('Laptops', LaptopComputer.objects.count(), 'bi-laptop'),
            ('Servers', ServerComputer.objects.count(), 'bi-server'),
            ('Printers', Printer.objects.count(), 'bi-printer'),
            ('UPS Units', Ups.objects.count(), 'bi-battery-charging'),
            ('Switches', Switch.objects.count(), 'bi-hdd-rack'),
            ('Access Points', AccessPoint.objects.count(), 'bi-router'),
            ('Phones', Phone.objects.count(), 'bi-telephone'),
        ]),
        ('Network ping', 'bi-broadcast-pin', [
            ('Registered IP addresses', len(pingable_ips), 'bi-hdd-network'),
            ('Reachable devices', reachable_count, 'bi-check-circle'),
            ('Failed devices', unreachable_count, 'bi-x-circle'),
        ]),
    ]
    statistics_routes = {
        'Cities': reverse('cities-list'),
        'Areas': reverse('areas-list'),
        'Buildings': reverse('buildings-list'),
        'Floors': reverse('floors-list'),
        'Rooms': reverse('rooms-list'),
        'Spaces': reverse('spaces-list'),
        'Common areas': reverse('common-areas-list'),
        'Sockets': reverse('sockets-list'),
        'General directorates': reverse('general-directorates-list'),
        'Directorates': reverse('directorates-list'),
        'Departments': reverse('departments-list'),
        'Offices': reverse('offices-list'),
        'Users': reverse('users-list'),
        'Assignments': reverse('assignments-list'),
        'Peripherals': reverse('peripherals-list'),
        'All devices': reverse('devices-list'),
        'Desktops': reverse('desktops-list'),
        'All-In-Ones': reverse('allInOnes-list'),
        'Laptops': reverse('laptops-list'),
        'Servers': reverse('servers-list'),
        'Printers': reverse('printers-list'),
        'UPS Units': reverse('upses-list'),
        'Switches': reverse('switches-list'),
        'Access Points': reverse('access-points-list'),
        'Phones': reverse('phones-list'),
        'Registered IP addresses': reverse('ping-all-devices'),
        'Reachable devices': reverse('ping-all-devices') + '?status=reachable',
        'Failed devices': reverse('ping-all-devices') + '?status=failed',
    }
    statistics_sections = [
        (section, icon, [
            (label, count, item_icon, statistics_routes[label])
            for label, count, item_icon in entries
        ])
        for section, icon, entries in statistics_sections
    ]
    statistics_charts = [
        (
            'Devices by type',
            [entry[0] for entry in statistics_sections[3][2]],
            [entry[1] for entry in statistics_sections[3][2]],
            [entry[3] for entry in statistics_sections[3][2]],
        ),
        (
            'Assignment status',
            ['Assigned devices', 'Unassigned devices'],
            [assigned_devices, total_devices - assigned_devices],
            [
                reverse('devices-list') + '?assignment_status=assigned',
                reverse('devices-list') + '?assignment_status=unassigned',
            ],
        ),
        (
            'Ping status',
            ['Reachable', 'Failed'],
            [reachable_count, unreachable_count],
            [
                reverse('ping-all-devices') + '?status=reachable',
                reverse('ping-all-devices') + '?status=failed',
            ],
        ),
    ]
    return render(request, 'inventory/device-statistics.html', {
        'total_devices': total_devices,
        'assigned_devices': assigned_devices,
        'unassigned_devices': total_devices - assigned_devices,
        'statistics_sections': statistics_sections,
        'statistics_charts': [
            {
                'title': title,
                'labels': json.dumps(labels),
                'values': json.dumps(values),
                'urls': json.dumps(urls),
            }
            for title, labels, values, urls in statistics_charts
        ],
    })


# ─────────────────────────────────────────────────────────────────────────────
# ORGANIZATIONAL STRUCTURE VIEWS
# ─────────────────────────────────────────────────────────────────────────────

def general_directorates_list(request):
    general_directorates = GeneralDirectorate.objects.annotate(
        directorates_count=Count('directorates', distinct=True),
        departments_count=Count('directorates__departments', distinct=True),
        offices_count=Count('directorates__departments__offices', distinct=True),
        users_count=Count('directorates__departments__users', distinct=True),
    )
    return render(request, 'inventory/general-directorates-list.html',
                  {'general_directorates': general_directorates})

def general_directorate_detail(request, pk):
    general_directorate = get_object_or_404(
        GeneralDirectorate.objects.annotate(
            directorates_count=Count('directorates', distinct=True),
            departments_count=Count('directorates__departments', distinct=True),
            offices_count=Count('directorates__departments__offices', distinct=True),
            users_count=Count('directorates__departments__users', distinct=True),
        ),
        pk=pk
    )
    return render(request, 'inventory/general-directorate-detail.html',
                  {'general_directorate': general_directorate})

def new_general_directorate(request):
    return handle_create(request, GeneralDirectorateForm, 'general-directorates-list')

def update_general_directorate(request, pk):
    return handle_update(request, GeneralDirectorateForm, 'general-directorates-list', pk)

def delete_general_directorate(request, pk):
    return handle_delete(request, GeneralDirectorate, 'general-directorates-list', pk)



def directorates_list(request):
    # Load the parent organization in the same query.
    directorates = Directorate.objects.select_related('general_directorate').annotate(
        departments_count=Count('departments', distinct=True),
        offices_count=Count('departments__offices', distinct=True),
        users_count=Count('departments__users', distinct=True),
    )
    if request.GET.get('general_directorate'):
        directorates = directorates.filter(general_directorate_id=request.GET['general_directorate'])
    return render(request, 'inventory/directorates-list.html', {'directorates': directorates})

def directorate_detail(request, pk):
    directorate = get_object_or_404(
        Directorate.objects.select_related('general_directorate').annotate(
            departments_count=Count('departments', distinct=True),
            offices_count=Count('departments__offices', distinct=True),
            users_count=Count('departments__users', distinct=True),
        ),
        pk=pk
    )
    return render(request, 'inventory/directorate-detail.html', {'directorate': directorate})   

def new_directorate(request):
    return handle_create(request, DirectorateForm, 'directorates-list')

def update_directorate(request, pk):
    return handle_update(request, DirectorateForm, 'directorates-list', pk)

def delete_directorate(request, pk):
    return handle_delete(request, Directorate, 'directorates-list', pk)



def departments_list(request):
    departments = Department.objects.select_related(
        'directorate__general_directorate'  # Load 2 levels up in one JOIN
    ).annotate(
        offices_count=Count('offices', distinct=True),
        users_count=Count('users', distinct=True),
    )
    if request.GET.get('general_directorate'):
        departments = departments.filter(directorate__general_directorate_id=request.GET['general_directorate'])
    if request.GET.get('directorate'):
        departments = departments.filter(directorate_id=request.GET['directorate'])
    return render(request, 'inventory/departments-list.html', {'departments': departments})
def department_detail(request, pk):
    department = get_object_or_404(
        Department.objects.select_related(
            'directorate__general_directorate'  # Load 2 levels up in one JOIN
        ).annotate(
            offices_count=Count('offices', distinct=True),
            users_count=Count('users', distinct=True),
        ),
        pk=pk
    )
    return render(request, 'inventory/department-detail.html', {'department': department})


def new_department(request):
    return handle_create(request, DepartmentForm, 'departments-list')

def update_department(request, pk):
    return handle_update(request, DepartmentForm, 'departments-list', pk)

def delete_department(request, pk):
    return handle_delete(request, Department, 'departments-list', pk)





def offices_list(request):
    offices = Office.objects.select_related(
        'department__directorate__general_directorate'  # Load 3 levels up in one JOIN
    ).annotate(
        users_count=Count('users', distinct=True),
    )
    if request.GET.get('general_directorate'):
        offices = offices.filter(department__directorate__general_directorate_id=request.GET['general_directorate'])
    if request.GET.get('directorate'):
        offices = offices.filter(department__directorate_id=request.GET['directorate'])
    if request.GET.get('department'):
        offices = offices.filter(department_id=request.GET['department'])
    return render(request, 'inventory/offices-list.html', {'offices': offices})

def office_detail(request, pk):
    office = get_object_or_404(
        Office.objects.select_related(
            'department__directorate__general_directorate'  # Load 3 levels up in one JOIN
        ).annotate(
            users_count=Count('users', distinct=True),
        ),
        pk=pk
    )
    return render(request, 'inventory/office-detail.html', {'office': office})

def new_office(request):
    return handle_create(request, OfficeForm, 'offices-list')

def update_office(request, pk):
    return handle_update(request, OfficeForm, 'offices-list', pk)

def delete_office(request, pk):
    return handle_delete(request, Office, 'offices-list', pk)


# ─────────────────────────────────────────────────────────────────────────────
# GEOGRAPHICAL STRUCTURE VIEWS
# ─────────────────────────────────────────────────────────────────────────────
# Location totals combine devices assigned through Spaces and Common Areas.

def cities_list(request):
    # Separate paths are combined below.
    _ca = "areas__buildings__floors__common_areas__"   # path through CommonArea
    _sp = "areas__buildings__floors__rooms__spaces__"  # path through Space

    cities = City.objects.annotate(
        areas_count=Count("areas", distinct=True),
        buildings_count=Count("areas__buildings", distinct=True),
        floors_count=Count("areas__buildings__floors", distinct=True),

        # Devices assigned through Spaces.
        _desktops_sp=Count(_sp + "devices__desktopcomputer", distinct=True),
        _allinones_sp=Count(_sp + "devices__allinonecomputer", distinct=True),
        _laptops_sp=Count(_sp + "devices__laptopcomputer", distinct=True),
        _printers_sp=Count(_sp + "devices__printer", distinct=True),
        _ups_sp=Count(_sp + "devices__ups", distinct=True),
        _servers_sp=Count(_sp + "devices__servercomputer", distinct=True),
        _switches_sp=Count(_sp + "devices__switch", distinct=True),
        _accesspoints_sp=Count(_sp + "devices__accesspoint", distinct=True),
        _phones_sp=Count(_sp + "devices__phone", distinct=True),
        _peripherals_sp=Count(_sp + "devices__peripherals", distinct=True),
        _sockets_sp=Count(_sp + "sockets", distinct=True),

        # Devices assigned through Common Areas.
        _desktops_ca=Count(_ca + "devices__desktopcomputer", distinct=True),
        _allinones_ca=Count(_ca + "devices__allinonecomputer", distinct=True),
        _laptops_ca=Count(_ca + "devices__laptopcomputer", distinct=True),
        _printers_ca=Count(_ca + "devices__printer", distinct=True),
        _ups_ca=Count(_ca + "devices__ups", distinct=True),
        _servers_ca=Count(_ca + "devices__servercomputer", distinct=True),
        _switches_ca=Count(_ca + "devices__switch", distinct=True),
        _accesspoints_ca=Count(_ca + "devices__accesspoint", distinct=True),
        _phones_ca=Count(_ca + "devices__phone", distinct=True),
        _peripherals_ca=Count(_ca + "devices__peripherals", distinct=True),
        _sockets_ca=Count(_ca + "sockets", distinct=True),

    ).annotate(
        # Combine both location paths for the templates.
        desktops_count=ExpressionWrapper(F("_desktops_sp") + F("_desktops_ca"), output_field=IntegerField()),
        allinones_count=ExpressionWrapper(F("_allinones_sp") + F("_allinones_ca"), output_field=IntegerField()),
        laptops_count=ExpressionWrapper(F("_laptops_sp") + F("_laptops_ca"), output_field=IntegerField()),
        printers_count=ExpressionWrapper(F("_printers_sp") + F("_printers_ca"), output_field=IntegerField()),
        ups_count=ExpressionWrapper(F("_ups_sp") + F("_ups_ca"), output_field=IntegerField()),
        servers_count=ExpressionWrapper(F("_servers_sp") + F("_servers_ca"), output_field=IntegerField()),
        switches_count=ExpressionWrapper(F("_switches_sp") + F("_switches_ca"), output_field=IntegerField()),
        accesspoints_count=ExpressionWrapper(F("_accesspoints_sp") + F("_accesspoints_ca"), output_field=IntegerField()),
        phones_count=ExpressionWrapper(F("_phones_sp") + F("_phones_ca"), output_field=IntegerField()),
        peripherals_count=ExpressionWrapper(F("_peripherals_sp") + F("_peripherals_ca"), output_field=IntegerField()),
        sockets_count=ExpressionWrapper(F("_sockets_sp") + F("_sockets_ca"), output_field=IntegerField()),
    )
    return render(request, "inventory/cities-list.html", {"cities": cities})


def city_detail(request, pk):
    # Use the same location paths as the list view.
    _ca = "areas__buildings__floors__common_areas__"   # path through CommonArea
    _sp = "areas__buildings__floors__rooms__spaces__"  # path through Space

    city = get_object_or_404(
        City.objects.annotate(
            areas_count=Count("areas", distinct=True),
            buildings_count=Count("areas__buildings", distinct=True),
            floors_count=Count("areas__buildings__floors", distinct=True),

            # Devices assigned through Spaces.
            _desktops_sp=Count(_sp + "devices__desktopcomputer", distinct=True),
            _allinones_sp=Count(_sp + "devices__allinonecomputer", distinct=True),
            _laptops_sp=Count(_sp + "devices__laptopcomputer", distinct=True),
            _printers_sp=Count(_sp + "devices__printer", distinct=True),
            _ups_sp=Count(_sp + "devices__ups", distinct=True),
            _servers_sp=Count(_sp + "devices__servercomputer", distinct=True),
            _switches_sp=Count(_sp + "devices__switch", distinct=True),
            _accesspoints_sp=Count(_sp + "devices__accesspoint", distinct=True),
            _phones_sp=Count(_sp + "devices__phone", distinct=True),
            _peripherals_sp=Count(_sp + "devices__peripherals", distinct=True),
            _sockets_sp=Count(_sp + "sockets", distinct=True),

            # Devices assigned through Common Areas.
            _desktops_ca=Count(_ca + "devices__desktopcomputer", distinct=True),
            _allinones_ca=Count(_ca + "devices__allinonecomputer", distinct=True),
            _laptops_ca=Count(_ca + "devices__laptopcomputer", distinct=True),
            _printers_ca=Count(_ca + "devices__printer", distinct=True),
            _ups_ca=Count(_ca + "devices__ups", distinct=True),
            _servers_ca=Count(_ca + "devices__servercomputer", distinct=True),
            _switches_ca=Count(_ca + "devices__switch", distinct=True),
            _accesspoints_ca=Count(_ca + "devices__accesspoint", distinct=True),
            _phones_ca=Count(_ca + "devices__phone", distinct=True),
            _peripherals_ca=Count(_ca + "devices__peripherals", distinct=True),
            _sockets_ca=Count(_ca + "sockets", distinct=True),
        ).annotate(
            # Combine both location paths.
            desktops_count=ExpressionWrapper(F("_desktops_sp") + F("_desktops_ca"), output_field=IntegerField()),
            allinones_count=ExpressionWrapper(F("_allinones_sp") + F("_allinones_ca"), output_field=IntegerField()),
            laptops_count=ExpressionWrapper(F("_laptops_sp") + F("_laptops_ca"), output_field=IntegerField()),
            printers_count=ExpressionWrapper(F("_printers_sp") + F("_printers_ca"), output_field=IntegerField()),
            ups_count=ExpressionWrapper(F("_ups_sp") + F("_ups_ca"), output_field=IntegerField()),
            servers_count=ExpressionWrapper(F("_servers_sp") + F("_servers_ca"), output_field=IntegerField()),
            switches_count=ExpressionWrapper(F("_switches_sp") + F("_switches_ca"), output_field=IntegerField()),
            accesspoints_count=ExpressionWrapper(F("_accesspoints_sp") + F("_accesspoints_ca"), output_field=IntegerField()),
            phones_count=ExpressionWrapper(F("_phones_sp") + F("_phones_ca"), output_field=IntegerField()),
            peripherals_count=ExpressionWrapper(F("_peripherals_sp") + F("_peripherals_ca"), output_field=IntegerField()),
            sockets_count=ExpressionWrapper(F("_sockets_sp") + F("_sockets_ca"), output_field=IntegerField()),
        ),
        pk=pk
    )

    areas = city.areas.all()

    context = {
        "city": city,
        "areas": areas,
        "location_query": f"location_type=city&location_id={city.pk}",
    }
    return render(request, "inventory/city-detail.html", context)

def new_city(request):
    return handle_create(request, CityForm, 'cities-list')

def update_city(request, pk):
    return handle_update(request, CityForm, 'cities-list', pk)

def delete_city(request, pk):
    return handle_delete(request, City, 'cities-list', pk)


def areas_list(request):
    # Combine devices assigned through Spaces and Common Areas.
    _ca = "buildings__floors__common_areas__"
    _sp = "buildings__floors__rooms__spaces__"

    areas = Area.objects.select_related("city").annotate(
        buildings_count=Count("buildings", distinct=True),
        floors_count=Count("buildings__floors", distinct=True),
        _desktops_sp=Count(_sp + "devices__desktopcomputer", distinct=True),
        _allinones_sp=Count(_sp + "devices__allinonecomputer", distinct=True),
        _laptops_sp=Count(_sp + "devices__laptopcomputer", distinct=True),
        _servers_sp=Count(_sp + "devices__servercomputer", distinct=True),
        _printers_sp=Count(_sp + "devices__printer", distinct=True),
        _ups_sp=Count(_sp + "devices__ups", distinct=True),
        _switches_sp=Count(_sp + "devices__switch", distinct=True),
        _accesspoints_sp=Count(_sp + "devices__accesspoint", distinct=True),
        _phones_sp=Count(_sp + "devices__phone", distinct=True),
        _peripherals_sp=Count(_sp + "devices__peripherals", distinct=True),
        _sockets_sp=Count(_sp + "sockets", distinct=True),
        _desktops_ca=Count(_ca + "devices__desktopcomputer", distinct=True),
        _allinones_ca=Count(_ca + "devices__allinonecomputer", distinct=True),
        _laptops_ca=Count(_ca + "devices__laptopcomputer", distinct=True),
        _servers_ca=Count(_ca + "devices__servercomputer", distinct=True),
        _printers_ca=Count(_ca + "devices__printer", distinct=True),
        _ups_ca=Count(_ca + "devices__ups", distinct=True),
        _switches_ca=Count(_ca + "devices__switch", distinct=True),
        _accesspoints_ca=Count(_ca + "devices__accesspoint", distinct=True),
        _phones_ca=Count(_ca + "devices__phone", distinct=True),
        _peripherals_ca=Count(_ca + "devices__peripherals", distinct=True),
        _sockets_ca=Count(_ca + "sockets", distinct=True),
    ).annotate(
        desktops_count=ExpressionWrapper(F("_desktops_sp") + F("_desktops_ca"), output_field=IntegerField()),
        allinones_count=ExpressionWrapper(F("_allinones_sp") + F("_allinones_ca"), output_field=IntegerField()),
        laptops_count=ExpressionWrapper(F("_laptops_sp") + F("_laptops_ca"), output_field=IntegerField()),
        servers_count=ExpressionWrapper(F("_servers_sp") + F("_servers_ca"), output_field=IntegerField()),
        printers_count=ExpressionWrapper(F("_printers_sp") + F("_printers_ca"), output_field=IntegerField()),
        ups_count=ExpressionWrapper(F("_ups_sp") + F("_ups_ca"), output_field=IntegerField()),
        switches_count=ExpressionWrapper(F("_switches_sp") + F("_switches_ca"), output_field=IntegerField()),
        accesspoints_count=ExpressionWrapper(F("_accesspoints_sp") + F("_accesspoints_ca"), output_field=IntegerField()),
        phones_count=ExpressionWrapper(F("_phones_sp") + F("_phones_ca"), output_field=IntegerField()),
        peripherals_count=ExpressionWrapper(F("_peripherals_sp") + F("_peripherals_ca"), output_field=IntegerField()),
        sockets_count=ExpressionWrapper(F("_sockets_sp") + F("_sockets_ca"), output_field=IntegerField()),
    )
    areas = _filter_by_location(areas, request, {"city": "city_id"})
    return render(request, "inventory/areas-list.html", {"areas": areas})

def area_detail(request, pk):
    _ca = "buildings__floors__common_areas__"
    _sp = "buildings__floors__rooms__spaces__"

    area = get_object_or_404(
        Area.objects.select_related("city").annotate(
            buildings_count=Count("buildings", distinct=True),
            floors_count=Count("buildings__floors", distinct=True),
            _desktops_sp=Count(_sp + "devices__desktopcomputer", distinct=True),
            _allinones_sp=Count(_sp + "devices__allinonecomputer", distinct=True),
            _laptops_sp=Count(_sp + "devices__laptopcomputer", distinct=True),
            _servers_sp=Count(_sp + "devices__servercomputer", distinct=True),
            _printers_sp=Count(_sp + "devices__printer", distinct=True),
            _ups_sp=Count(_sp + "devices__ups", distinct=True),
            _switches_sp=Count(_sp + "devices__switch", distinct=True),
            _accesspoints_sp=Count(_sp + "devices__accesspoint", distinct=True),
            _phones_sp=Count(_sp + "devices__phone", distinct=True),
            _peripherals_sp=Count(_sp + "devices__peripherals", distinct=True),
            _sockets_sp=Count(_sp + "sockets", distinct=True),
            _desktops_ca=Count(_ca + "devices__desktopcomputer", distinct=True),
            _allinones_ca=Count(_ca + "devices__allinonecomputer", distinct=True),
            _laptops_ca=Count(_ca + "devices__laptopcomputer", distinct=True),
            _servers_ca=Count(_ca + "devices__servercomputer", distinct=True),
            _printers_ca=Count(_ca + "devices__printer", distinct=True),
            _ups_ca=Count(_ca + "devices__ups", distinct=True),
            _switches_ca=Count(_ca + "devices__switch", distinct=True),
            _accesspoints_ca=Count(_ca + "devices__accesspoint", distinct=True),
            _phones_ca=Count(_ca + "devices__phone", distinct=True),
            _peripherals_ca=Count(_ca + "devices__peripherals", distinct=True),
            _sockets_ca=Count(_ca + "sockets", distinct=True),
        ).annotate(
            desktops_count=ExpressionWrapper(F("_desktops_sp") + F("_desktops_ca"), output_field=IntegerField()),
            allinones_count=ExpressionWrapper(F("_allinones_sp") + F("_allinones_ca"), output_field=IntegerField()),
            laptops_count=ExpressionWrapper(F("_laptops_sp") + F("_laptops_ca"), output_field=IntegerField()),
            servers_count=ExpressionWrapper(F("_servers_sp") + F("_servers_ca"), output_field=IntegerField()),
            printers_count=ExpressionWrapper(F("_printers_sp") + F("_printers_ca"), output_field=IntegerField()),
            ups_count=ExpressionWrapper(F("_ups_sp") + F("_ups_ca"), output_field=IntegerField()),
            switches_count=ExpressionWrapper(F("_switches_sp") + F("_switches_ca"), output_field=IntegerField()),
            accesspoints_count=ExpressionWrapper(F("_accesspoints_sp") + F("_accesspoints_ca"), output_field=IntegerField()),
            phones_count=ExpressionWrapper(F("_phones_sp") + F("_phones_ca"), output_field=IntegerField()),
            peripherals_count=ExpressionWrapper(F("_peripherals_sp") + F("_peripherals_ca"), output_field=IntegerField()),
            sockets_count=ExpressionWrapper(F("_sockets_sp") + F("_sockets_ca"), output_field=IntegerField()),
        ),
        pk=pk
    )

    return render(request, "inventory/area-detail.html", {
        "area": area,
        "location_query": f"location_type=area&location_id={area.pk}",
    })

def new_area(request):
    return handle_create(request, AreaForm, 'areas-list')

def update_area(request, pk):
    return handle_update(request, AreaForm, 'areas-list', pk)

def delete_area(request, pk):
    return handle_delete(request, Area, 'areas-list', pk)


def buildings_list(request):
    # Building-level location paths.
    _sp = "floors__rooms__spaces__"
    _ca = "floors__common_areas__"

    buildings = Building.objects.select_related("area__city").annotate(
        floors_count=Count("floors", distinct=True),
        rooms_count=Count("floors__rooms", distinct=True),
        common_areas_count=Count("floors__common_areas", distinct=True),
        _desktops_sp=Count(_sp + "devices__desktopcomputer", distinct=True),
        _allinones_sp=Count(_sp + "devices__allinonecomputer", distinct=True),
        _laptops_sp=Count(_sp + "devices__laptopcomputer", distinct=True),
        _servers_sp=Count(_sp + "devices__servercomputer", distinct=True),
        _printers_sp=Count(_sp + "devices__printer", distinct=True),
        _ups_sp=Count(_sp + "devices__ups", distinct=True),
        _switches_sp=Count(_sp + "devices__switch", distinct=True),
        _accesspoints_sp=Count(_sp + "devices__accesspoint", distinct=True),
        _phones_sp=Count(_sp + "devices__phone", distinct=True),
        _peripherals_sp=Count(_sp + "devices__peripherals", distinct=True),
        _sockets_sp=Count(_sp + "sockets", distinct=True),
        _desktops_ca=Count(_ca + "devices__desktopcomputer", distinct=True),
        _allinones_ca=Count(_ca + "devices__allinonecomputer", distinct=True),
        _laptops_ca=Count(_ca + "devices__laptopcomputer", distinct=True),
        _servers_ca=Count(_ca + "devices__servercomputer", distinct=True),
        _printers_ca=Count(_ca + "devices__printer", distinct=True),
        _ups_ca=Count(_ca + "devices__ups", distinct=True),
        _switches_ca=Count(_ca + "devices__switch", distinct=True),
        _accesspoints_ca=Count(_ca + "devices__accesspoint", distinct=True),
        _phones_ca=Count(_ca + "devices__phone", distinct=True),
        _peripherals_ca=Count(_ca + "devices__peripherals", distinct=True),
        _sockets_ca=Count(_ca + "sockets", distinct=True),
    ).annotate(
        desktops_count=F("_desktops_sp") + F("_desktops_ca"),
        allinones_count=F("_allinones_sp") + F("_allinones_ca"),
        laptops_count=F("_laptops_sp") + F("_laptops_ca"),
        servers_count=F("_servers_sp") + F("_servers_ca"),
        printers_count=F("_printers_sp") + F("_printers_ca"),
        ups_count=F("_ups_sp") + F("_ups_ca"),
        switches_count=F("_switches_sp") + F("_switches_ca"),
        accesspoints_count=F("_accesspoints_sp") + F("_accesspoints_ca"),
        phones_count=F("_phones_sp") + F("_phones_ca"),
        peripherals_count=F("_peripherals_sp") + F("_peripherals_ca"),
        sockets_count=F("_sockets_sp") + F("_sockets_ca"),
    )
    buildings = _filter_by_location(buildings, request, {"city": "area__city_id", "area": "area_id"})
    return render(request, "inventory/buildings-list.html", {"buildings": buildings})

def building_detail(request, pk):
    # Combine devices assigned through Spaces and Common Areas.
    _sp = "floors__rooms__spaces__"
    _ca = "floors__common_areas__"

    building = get_object_or_404(
        Building.objects.select_related("area__city").annotate(
            floors_count=Count("floors", distinct=True),
            rooms_count=Count("floors__rooms", distinct=True),
            common_areas_count=Count("floors__common_areas", distinct=True),
            _desktops_sp=Count(_sp + "devices__desktopcomputer", distinct=True),
            _allinones_sp=Count(_sp + "devices__allinonecomputer", distinct=True),
            _laptops_sp=Count(_sp + "devices__laptopcomputer", distinct=True),
            _servers_sp=Count(_sp + "devices__servercomputer", distinct=True),
            _printers_sp=Count(_sp + "devices__printer", distinct=True),
            _ups_sp=Count(_sp + "devices__ups", distinct=True),
            _switches_sp=Count(_sp + "devices__switch", distinct=True),
            _accesspoints_sp=Count(_sp + "devices__accesspoint", distinct=True),
            _phones_sp=Count(_sp + "devices__phone", distinct=True),
            _peripherals_sp=Count(_sp + "devices__peripherals", distinct=True),
            _sockets_sp=Count(_sp + "sockets", distinct=True),
            _desktops_ca=Count(_ca + "devices__desktopcomputer", distinct=True),
            _allinones_ca=Count(_ca + "devices__allinonecomputer", distinct=True),
            _laptops_ca=Count(_ca + "devices__laptopcomputer", distinct=True),
            _servers_ca=Count(_ca + "devices__servercomputer", distinct=True),
            _printers_ca=Count(_ca + "devices__printer", distinct=True),
            _ups_ca=Count(_ca + "devices__ups", distinct=True),
            _switches_ca=Count(_ca + "devices__switch", distinct=True),
            _accesspoints_ca=Count(_ca + "devices__accesspoint", distinct=True),
            _phones_ca=Count(_ca + "devices__phone", distinct=True),
            _peripherals_ca=Count(_ca + "devices__peripherals", distinct=True),
            _sockets_ca=Count(_ca + "sockets", distinct=True),
        ).annotate(
            desktops_count=F("_desktops_sp") + F("_desktops_ca"),
            allinones_count=F("_allinones_sp") + F("_allinones_ca"),
            laptops_count=F("_laptops_sp") + F("_laptops_ca"),
            servers_count=F("_servers_sp") + F("_servers_ca"),
            printers_count=F("_printers_sp") + F("_printers_ca"),       
            ups_count=F("_ups_sp") + F("_ups_ca"),
            switches_count=F("_switches_sp") + F("_switches_ca"),
            accesspoints_count=F("_accesspoints_sp") + F("_accesspoints_ca"),
            phones_count=F("_phones_sp") + F("_phones_ca"),
            peripherals_count=F("_peripherals_sp") + F("_peripherals_ca"),
            sockets_count=F("_sockets_sp") + F("_sockets_ca"),
        ),
        pk=pk
    )
    return render(request, "inventory/building-detail.html", {
        "building": building,
        "location_query": f"location_type=building&location_id={building.pk}",
    })

def new_building(request):
    return handle_create(request, BuildingForm, 'buildings-list')

def update_building(request, pk):
    return handle_update(request, BuildingForm, 'buildings-list', pk)

def delete_building(request, pk):
    return handle_delete(request, Building, 'buildings-list', pk)

def floors_list(request):
    # Combine devices assigned through Spaces and Common Areas.
    _sp = "rooms__spaces__"
    _ca = "common_areas__"

    floors = Floor.objects.select_related("building__area__city").annotate(
        rooms_count=Count("rooms", distinct=True),
        common_areas_count=Count("common_areas", distinct=True),
        _desktops_sp=Count(_sp + "devices__desktopcomputer", distinct=True),
        _allinones_sp=Count(_sp + "devices__allinonecomputer", distinct=True),
        _laptops_sp=Count(_sp + "devices__laptopcomputer", distinct=True),
        _servers_sp=Count(_sp + "devices__servercomputer", distinct=True),
        _printers_sp=Count(_sp + "devices__printer", distinct=True),
        _ups_sp=Count(_sp + "devices__ups", distinct=True),
        _switches_sp=Count(_sp + "devices__switch", distinct=True),
        _accesspoints_sp=Count(_sp + "devices__accesspoint", distinct=True),
        _phones_sp=Count(_sp + "devices__phone", distinct=True),
        _peripherals_sp=Count(_sp + "devices__peripherals", distinct=True),
        _sockets_sp=Count(_sp + "sockets", distinct=True),
        _desktops_ca=Count(_ca + "devices__desktopcomputer", distinct=True),
        _allinones_ca=Count(_ca + "devices__allinonecomputer", distinct=True),
        _laptops_ca=Count(_ca + "devices__laptopcomputer", distinct=True),
        _servers_ca=Count(_ca + "devices__servercomputer", distinct=True),
        _printers_ca=Count(_ca + "devices__printer", distinct=True),
        _ups_ca=Count(_ca + "devices__ups", distinct=True),
        _switches_ca=Count(_ca + "devices__switch", distinct=True),
        _accesspoints_ca=Count(_ca + "devices__accesspoint", distinct=True),
        _phones_ca=Count(_ca + "devices__phone", distinct=True),
        _peripherals_ca=Count(_ca + "devices__peripherals", distinct=True),
        _sockets_ca=Count(_ca + "sockets", distinct=True),
    ).annotate(
        desktops_count=F("_desktops_sp") + F("_desktops_ca"),
        allinones_count=F("_allinones_sp") + F("_allinones_ca"),
        laptops_count=F("_laptops_sp") + F("_laptops_ca"),
        servers_count=F("_servers_sp") + F("_servers_ca"),
        printers_count=F("_printers_sp") + F("_printers_ca"),
        ups_count=F("_ups_sp") + F("_ups_ca"),
        switches_count=F("_switches_sp") + F("_switches_ca"),
        accesspoints_count=F("_accesspoints_sp") + F("_accesspoints_ca"),
        phones_count=F("_phones_sp") + F("_phones_ca"),
        peripherals_count=F("_peripherals_sp") + F("_peripherals_ca"),
        sockets_count=F("_sockets_sp") + F("_sockets_ca"),
    )
    floors = _filter_by_location(floors, request, {"building": "building_id"})
    return render(request, "inventory/floors-list.html", {"floors": floors})

def floor_detail(request, pk):
    # Combine devices assigned through Spaces and Common Areas.
    _sp = "rooms__spaces__"
    _ca = "common_areas__"

    floor = get_object_or_404(
        Floor.objects.select_related("building__area__city").annotate(
            rooms_count=Count("rooms", distinct=True),
            common_areas_count=Count("common_areas", distinct=True),
            _desktops_sp=Count(_sp + "devices__desktopcomputer", distinct=True),
            _allinones_sp=Count(_sp + "devices__allinonecomputer", distinct=True),
            _laptops_sp=Count(_sp + "devices__laptopcomputer", distinct=True),
            _servers_sp=Count(_sp + "devices__servercomputer", distinct=True),
            _printers_sp=Count(_sp + "devices__printer", distinct=True),
            _ups_sp=Count(_sp + "devices__ups", distinct=True),
            _switches_sp=Count(_sp + "devices__switch", distinct=True),
            _accesspoints_sp=Count(_sp + "devices__accesspoint", distinct=True),
            _phones_sp=Count(_sp + "devices__phone", distinct=True),
            _peripherals_sp=Count(_sp + "devices__peripherals", distinct=True),
            _sockets_sp=Count(_sp + "sockets", distinct=True),
            _desktops_ca=Count(_ca + "devices__desktopcomputer", distinct=True),
            _allinones_ca=Count(_ca + "devices__allinonecomputer", distinct=True),
            _laptops_ca=Count(_ca + "devices__laptopcomputer", distinct=True),
            _servers_ca=Count(_ca + "devices__servercomputer", distinct=True),
            _printers_ca=Count(_ca + "devices__printer", distinct=True),
            _ups_ca=Count(_ca + "devices__ups", distinct=True),
            _switches_ca=Count(_ca + "devices__switch", distinct=True),
            _accesspoints_ca=Count(_ca + "devices__accesspoint", distinct=True),
            _phones_ca=Count(_ca + "devices__phone", distinct=True),
            _peripherals_ca=Count(_ca + "devices__peripherals", distinct=True),
            _sockets_ca=Count(_ca + "sockets", distinct=True),
        ).annotate(
            desktops_count=F("_desktops_sp") + F("_desktops_ca"),
            allinones_count=F("_allinones_sp") + F("_allinones_ca"),
            laptops_count=F("_laptops_sp") + F("_laptops_ca"),
            servers_count=F("_servers_sp") + F("_servers_ca"),
            printers_count=F("_printers_sp") + F("_printers_ca"),
            ups_count=F("_ups_sp") + F("_ups_ca"),
            switches_count=F("_switches_sp") + F("_switches_ca"),
            accesspoints_count=F("_accesspoints_sp") + F("_accesspoints_ca"),
            phones_count=F("_phones_sp") + F("_phones_ca"),
            peripherals_count=F("_peripherals_sp") + F("_peripherals_ca"),
            sockets_count=F("_sockets_sp") + F("_sockets_ca"),
        ),
        pk=pk
    )
    return render(request, "inventory/floor-detail.html", {
        "floor": floor,
        "location_query": f"location_type=floor&location_id={floor.pk}",
    })

def new_floor(request):
    return handle_create(request, FloorForm, 'floors-list')

def update_floor(request, pk):
    return handle_update(request, FloorForm, 'floors-list', pk)

def delete_floor(request, pk):
    return handle_delete(request, Floor, 'floors-list', pk)

def common_areas_list(request):
    # Common areas contain devices and sockets directly.
    common_areas = CommonArea.objects.select_related(
        "floor__building__area__city"
    ).annotate(
        desktops_count=Count("devices__desktopcomputer", distinct=True),
        allinones_count=Count("devices__allinonecomputer", distinct=True),
        laptops_count=Count("devices__laptopcomputer", distinct=True),
        servers_count=Count("devices__servercomputer", distinct=True),
        printers_count=Count("devices__printer", distinct=True),
        ups_count=Count("devices__ups", distinct=True),
        switches_count=Count("devices__switch", distinct=True),
        phones_count=Count("devices__phone", distinct=True),
        accesspoints_count=Count("devices__accesspoint", distinct=True),
        peripherals_count=Count("devices__peripherals", distinct=True),
        sockets_count=Count("sockets", distinct=True),
    )
    common_areas = _filter_by_location(common_areas, request, {
        "building": "floor__building_id",
        "floor": "floor_id",
        "common_area": "pk",
    })
    return render(request, "inventory/common-areas-list.html", {"common_areas": common_areas})

def common_area_detail(request, pk):
    common_area = get_object_or_404(
        CommonArea.objects.select_related(
            "floor__building__area__city"
        ).annotate(
            desktops_count=Count("devices__desktopcomputer", distinct=True),
            allinones_count=Count("devices__allinonecomputer", distinct=True),
            laptops_count=Count("devices__laptopcomputer", distinct=True),
            servers_count=Count("devices__servercomputer", distinct=True),
            printers_count=Count("devices__printer", distinct=True),
            ups_count=Count("devices__ups", distinct=True),
            switches_count=Count("devices__switch", distinct=True),
            phones_count=Count("devices__phone", distinct=True),
            accesspoints_count=Count("devices__accesspoint", distinct=True),
            peripherals_count=Count("devices__peripherals", distinct=True),
            sockets_count=Count("sockets", distinct=True),
        ),
        pk=pk
    )
    return render(request, "inventory/common-area-detail.html", {
        "common_area": common_area,
        "location_query": f"location_type=common_area&location_id={common_area.pk}",
    })

def new_common_area(request):
    return handle_create(request, CommonAreaForm, 'common-areas-list')

def update_common_area(request, pk):
    return handle_update(request, CommonAreaForm, 'common-areas-list', pk)

def delete_common_area(request, pk):
    return handle_delete(request, CommonArea, 'common-areas-list', pk)


def rooms_list(request):
    # Rooms count devices through their Spaces.
    rooms = Room.objects.select_related('floor__building__area__city').annotate(
        spaces_count=Count('spaces', distinct=True),
        desktops_count=Count('spaces__devices__desktopcomputer', distinct=True),
        allinones_count=Count('spaces__devices__allinonecomputer', distinct=True),
        laptops_count=Count('spaces__devices__laptopcomputer', distinct=True),
        servers_count=Count('spaces__devices__servercomputer', distinct=True),
        printers_count=Count('spaces__devices__printer', distinct=True),
        ups_count=Count('spaces__devices__ups', distinct=True),
        switches_count=Count('spaces__devices__switch', distinct=True),
        phones_count=Count('spaces__devices__phone', distinct=True),
        accesspoints_count=Count('spaces__devices__accesspoint', distinct=True),
        peripherals_count=Count('spaces__devices__peripherals', distinct=True),
        sockets_count=Count('spaces__sockets', distinct=True),
    )
    rooms = _filter_by_location(rooms, request, {
        "building": "floor__building_id",
        "floor": "floor_id",
    })
    return render(request, 'inventory/rooms-list.html', {'rooms': rooms})

def room_detail(request, pk):
    room = get_object_or_404(
        Room.objects.select_related('floor__building__area__city').annotate(
            spaces_count=Count('spaces', distinct=True),
            desktops_count=Count('spaces__devices__desktopcomputer', distinct=True),
            allinones_count=Count('spaces__devices__allinonecomputer', distinct=True),
            laptops_count=Count('spaces__devices__laptopcomputer', distinct=True),
            servers_count=Count('spaces__devices__servercomputer', distinct=True),
            printers_count=Count('spaces__devices__printer', distinct=True),
            ups_count=Count('spaces__devices__ups', distinct=True),
            switches_count=Count('spaces__devices__switch', distinct=True),
            phones_count=Count('spaces__devices__phone', distinct=True),
            accesspoints_count=Count('spaces__devices__accesspoint', distinct=True),
            peripherals_count=Count('spaces__devices__peripherals', distinct=True),
            sockets_count=Count('spaces__sockets', distinct=True),
        ),
        pk=pk
    )
    return render(request, 'inventory/room-detail.html', {
        'room': room,
        'location_query': f"location_type=room&location_id={room.pk}",
    })

def new_room(request):
    return handle_create(request, RoomForm, 'rooms-list')

def update_room(request, pk):
    return handle_update(request, RoomForm, 'rooms-list', pk)

def delete_room(request, pk):
    return handle_delete(request, Room, 'rooms-list', pk)


def spaces_list(request):
    # Spaces contain devices directly.
    spaces = Space.objects.select_related('room__floor__building__area__city').annotate(
        devices_count=Count('devices', distinct=True),
        sockets_count=Count('sockets', distinct=True),
        desktops_count=Count('devices__desktopcomputer', distinct=True),
        allinones_count=Count('devices__allinonecomputer', distinct=True),
        laptops_count=Count('devices__laptopcomputer', distinct=True),
        servers_count=Count('devices__servercomputer', distinct=True),
        printers_count=Count('devices__printer', distinct=True),
        ups_count=Count('devices__ups', distinct=True),
        switches_count=Count('devices__switch', distinct=True),
        phones_count=Count('devices__phone', distinct=True),
        accesspoints_count=Count('devices__accesspoint', distinct=True),
        peripherals_count=Count('devices__peripherals', distinct=True),
    )
    spaces = _filter_by_location(spaces, request, {
        'city': 'room__floor__building__area__city_id',
        'area': 'room__floor__building__area_id',
        'building': 'room__floor__building_id',
        'floor': 'room__floor_id',
        'room': 'room_id',
    })
    return render(request, 'inventory/spaces-list.html', {'spaces': spaces})

def space_detail(request, pk):  
    space = get_object_or_404(
        Space.objects.select_related('room__floor__building__area__city').annotate(
            devices_count=Count('devices', distinct=True),
            sockets_count=Count('sockets', distinct=True),
            desktops_count=Count('devices__desktopcomputer', distinct=True),
            allinones_count=Count('devices__allinonecomputer', distinct=True),
            laptops_count=Count('devices__laptopcomputer', distinct=True),
            servers_count=Count('devices__servercomputer', distinct=True),
            printers_count=Count('devices__printer', distinct=True),
            ups_count=Count('devices__ups', distinct=True),
            switches_count=Count('devices__switch', distinct=True),
            phones_count=Count('devices__phone', distinct=True),
            accesspoints_count=Count('devices__accesspoint', distinct=True),
            peripherals_count=Count('devices__peripherals', distinct=True),
        ),
        pk=pk
    )
    return render(request, 'inventory/space-detail.html', {
        'space': space,
        'location_query': f"location_type=space&location_id={space.pk}",
    })

def new_space(request):
    return handle_create(request, SpaceForm, 'spaces-list')

def update_space(request, pk):
    return handle_update(request, SpaceForm, 'spaces-list', pk)

def delete_space(request, pk):
    return handle_delete(request, Space, 'spaces-list', pk)

def sockets_list(request):
    # Load the full location chain in one query.
    sockets = Socket.objects.select_related(
        'space__room__floor__building__area__city',
        'common_area__floor__building__area__city',
    ).annotate(
        devices_count=Count('devices', distinct=True),
    )
    sockets = _filter_by_location(sockets, request, {
        'city': 'building__area__city_id',
        'area': 'building__area_id',
        'building': 'building_id',
        'floor': 'common_area__floor_id',
        'common_area': 'common_area_id',
        'room': 'space__room_id',
        'space': 'space_id',
    })
    return render(request, 'inventory/sockets-list.html', {'sockets': sockets})

def socket_detail(request, pk):
    socket = get_object_or_404(
        Socket.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
        ).annotate(
            devices_count=Count('devices', distinct=True),
        ),
        pk=pk
    )
    device_routes = {
        'desktopcomputer': 'desktop-detail',
        'allinonecomputer': 'allInOne-detail',
        'laptopcomputer': 'laptop-detail',
        'servercomputer': 'server-detail',
        'printer': 'printer-detail',
        'ups': 'ups-detail',
        'switch': 'switch-detail',
        'accesspoint': 'access-point-detail',
        'phone': 'phone-detail',
    }
    connected_devices = []
    for device in socket.devices.select_related().all():
        specific_device = device.get_specific_device()
        route_name = device_routes.get(specific_device._meta.model_name, 'device-detail')
        connected_devices.append({
            'title': f"Brand: {specific_device.brand} Serial: {specific_device.serial}",
            'url': reverse(route_name, kwargs={'pk': specific_device.pk}),
        })

    return render(request, 'inventory/socket-detail.html', {
        'socket': socket,
        'connected_devices': connected_devices,
    })

def new_socket(request):
    return handle_create(request, SocketForm, 'sockets-list')

def update_socket(request, pk):
    return handle_update(request, SocketForm, 'sockets-list', pk)

def delete_socket(request, pk):
    return handle_delete(request, Socket, 'sockets-list', pk)


# ─────────────────────────────────────────────────────────────────────────────
# PEOPLE VIEWS
# ─────────────────────────────────────────────────────────────────────────────

def assignments_list(request):
    assignments = Assignment.objects.select_related(
        'user',
        'device__space__room__floor__building__area__city',
        'device__common_area',
    ).order_by('user__email', 'assignment_date', 'pk')
    return render(request, 'inventory/assignments-list.html', {'assignments': assignments})

def assignment_detail(request, pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related(
            'user',
            'device__space__room__floor__building__area__city',
            'device__common_area',
        ),
        pk=pk
    )
    user_assignments = Assignment.objects.filter(user_id=assignment.user_id).select_related(
        'user',
        'device',
    ).order_by('assignment_date', 'pk')
    return render(request, 'inventory/assignment-detail.html', {
        'assignment': assignment,
        'user_assignments': user_assignments,
    })

def new_assignment(request):
    return handle_create(request, AssignmentForm, 'assignments-list')

def update_assignment(request, pk):
    return handle_update(request, AssignmentForm, 'assignments-list', pk)

def delete_assignment(request, pk):
    return handle_delete(request, Assignment, 'assignments-list', pk)


def _handover_user_value(users, value_getter):
    values = [value_getter(user) or 'Unregistered' for user in users]
    unique_values = list(dict.fromkeys(str(value) for value in values))
    if len(unique_values) == 1:
        common_suffix = ' (common)' if len(values) > 1 else ''
        return f'{unique_values[0]}{common_suffix}'
    return ', '.join(unique_values)


def material_handover(request):
    form = MaterialHandoverForm(request.POST or None, initial={
        'report_date': timezone.localdate(),
    })
    if request.method == 'POST' and form.is_valid():
        selected_users = form.cleaned_data['selected_users']
        report_user_values = {
            'general_directorate': _handover_user_value(
                selected_users, lambda user: user.general_directorate
            ),
            'directorate': _handover_user_value(
                selected_users, lambda user: user.directorate
            ),
            'department': _handover_user_value(
                selected_users, lambda user: user.department
            ),
            'office': _handover_user_value(
                selected_users, lambda user: user.office
            ),
            'full_name': _handover_user_value(
                selected_users, lambda user: f'{user.name} {user.surname}'
            ),
            'phone_email': _handover_user_value(
                selected_users,
                lambda user: f'{user.phone or "Unregistered"} - {user.email or "Unregistered"}',
            ),
        }
        locations = []
        for device in form.cleaned_data['selected_devices']:
            building = device.building
            if not building:
                continue
            location_parts = [
                building.area.city.name,
                building.area.name,
                building.name,
                building.address,
                building.postal_code,
            ]
            location = ' / '.join(str(part) for part in location_parts if part)
            if location and location not in locations:
                locations.append(location)
        return render(request, 'inventory/material-handover-report.html', {
            'form': form,
            'selected_users': selected_users,
            'report_user_values': report_user_values,
            'selected_devices': form.cleaned_data['selected_devices'],
            'location_address': ' ; '.join(locations) or '-',
            'report_date': form.cleaned_data['report_date'],
            'comments': form.cleaned_data['comments'],
        })
    return render(request, 'inventory/material-handover-form.html', {
        'form': form,
    })



def users_list(request):
    today = timezone.localdate()
    active_assignments = Assignment.objects.filter(
        assignment_date__lte=today,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).select_related('device__phone')
    # Load the full organization chain in one query.
    users = User.objects.select_related(
        'department__directorate__general_directorate',
        'office',
    ).prefetch_related(
        Prefetch(
            'assignment_set',
            queryset=active_assignments,
            to_attr='current_assignments',
        )
    )
    if request.GET.get('general_directorate'):
        users = users.filter(department__directorate__general_directorate_id=request.GET['general_directorate'])
    if request.GET.get('directorate'):
        users = users.filter(department__directorate_id=request.GET['directorate'])
    if request.GET.get('department'):
        users = users.filter(department_id=request.GET['department'])
    if request.GET.get('office'):
        users = users.filter(office_id=request.GET['office'])
    for user in users:
        user.assigned_phone_numbers = []
        for assignment in user.current_assignments:
            phone = getattr(assignment.device, 'phone', None)
            if phone and phone.phone_number is not None:
                phone_number = str(phone.phone_number)
                if phone_number not in user.assigned_phone_numbers:
                    user.assigned_phone_numbers.append(phone_number)
    return render(request, 'inventory/users-list.html', {'users': users})

def user_detail(request, pk):
    today = timezone.localdate()
    user = get_object_or_404(
        User.objects.select_related(
            'department__directorate__general_directorate',
            'office',
        ).prefetch_related(
            Prefetch(
                'assignment_set',
                queryset=Assignment.objects.select_related(
                    'device__space__room__floor__building__area__city',
                    'device__common_area__floor__building__area__city',
                    'device__laptopcomputer',
                    'device__desktopcomputer',
                    'device__allinonecomputer',
                    'device__servercomputer',
                    'device__printer',
                    'device__ups',
                    'device__accesspoint',
                    'device__switch',
                    'device__phone',
                ).order_by('assignment_type', 'device__brand', 'device__serial'),
                to_attr='device_assignments',
            )
        ),
        pk=pk
    )
    for assignment in user.device_assignments:
        specific_device = assignment.device.get_specific_device()
        assignment.device_detail_url = get_search_result_url(specific_device)
        assignment.assigned_phone_number = getattr(specific_device, 'phone_number', None)

    return render(request, 'inventory/user-detail.html', {'user': user, 'today': today})    

def new_user(request):
    return handle_create(request, UserForm, 'users-list')

def update_user(request, pk):
    return handle_update(request, UserForm, 'users-list', pk)

def delete_user(request, pk):
    return handle_delete(request, User, 'users-list', pk)


# ─────────────────────────────────────────────────────────────────────────────
# DEVICE VIEWS
# ─────────────────────────────────────────────────────────────────────────────

def _filter_by_location(queryset, request, paths):
    location_type = request.GET.get("location_type")
    location_id = request.GET.get("location_id")
    try:
        location_id = int(location_id)
    except (TypeError, ValueError):
        return queryset

    location_path = paths.get(location_type)
    if not location_path:
        return queryset

    if location_path.startswith('space__') or '__space__' in location_path:
        common_area_path = location_path.replace(
            'space__room__floor__', 'common_area__floor__', 1
        ).replace('space__room__', 'common_area__', 1)
        return queryset.filter(
            Q(**{location_path: location_id}) | Q(**{common_area_path: location_id})
        ).distinct()

    return queryset.filter(**{location_path: location_id}).distinct()

def devices_list(request):
    active_assignments = Assignment.objects.filter(
        Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate())
    ).select_related('user').order_by('user__surname', 'user__name')
    devices = Device.objects.select_related(
        'desktopcomputer',
        'allinonecomputer',
        'laptopcomputer',
        'servercomputer',
        'printer',
        'ups',
        'accesspoint',
        'switch',
        'phone',
        'space__room__floor__building__area__city',
        'common_area__floor__building__area__city',
    ).prefetch_related(
        Prefetch('assignments', queryset=active_assignments, to_attr='active_assignments')
    )
    assignment_status = request.GET.get('assignment_status')
    list_title = 'Devices'
    if assignment_status in {'assigned', 'unassigned'}:
        assigned_device_ids = active_assignments.values_list('device_id', flat=True)
        if assignment_status == 'assigned':
            devices = devices.filter(pk__in=assigned_device_ids)
            list_title = 'Assigned devices'
        else:
            devices = devices.exclude(pk__in=assigned_device_ids)
            list_title = 'Unassigned devices'

    devices = list(devices)
    for device in devices:
        device.detail_url = get_search_result_url(device.get_specific_device())

    return render(request, "inventory/devices-list.html", {
        "devices": devices,
        "list_title": list_title,
        "page_title": list_title,
        "show_assigned_user": assignment_status != 'unassigned',
    })

def device_detail(request, pk):
    device = get_object_or_404(
        Device.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
        ).prefetch_related(
            'assignments__user',
            'peripherals',
        ),
        pk=pk
    )
    return render(request, "inventory/hardware-detail.html", {
        "device": device,
        "page_icon": "bi bi-pc-display",
        "type_label": "Device",
        "specific_fields": [],
    })


def workstations_list(request):
    desktops = DesktopComputer.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related(
        'device_ptr__assignments__user',
        'device_ptr__peripherals',
    )
    allinones = AllInOneComputer.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related(
        'device_ptr__assignments__user',
        'device_ptr__peripherals',
    )
    laptops = LaptopComputer.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related(
        'device_ptr__assignments__user',
        'device_ptr__peripherals',
    )

    workstations = []
    for item in list(desktops) + list(allinones) + list(laptops):
        if isinstance(item, DesktopComputer):
            detail_url = reverse('desktop-detail', kwargs={'pk': item.pk})
        elif isinstance(item, AllInOneComputer):
            detail_url = reverse('allInOne-detail', kwargs={'pk': item.pk})
        else:
            detail_url = reverse('laptop-detail', kwargs={'pk': item.pk})

        workstations.append({
            'pk': item.pk,
            'brand': item.brand,
            'model': item.model,
            'serial': item.serial,
            'registration_code': item.registration_code,
            'ip_address': item.ip_address,
            'mac_address': item.mac_address,
            'usage_type': item.usage_type,
            'type': item.__class__.__name__,
            'type_label': item.__class__.__name__.replace('Computer', '').replace('AllInOne', 'All-In-One'),
            'device_type': item.__class__.__name__,
            'active_users': item.device_ptr.assignments.filter(
                Q(end_date__isnull=True) | Q(end_date__gte=timezone.now().date())
            ).select_related('user'),
            'detail_url': detail_url,
        })

    workstations = sorted(workstations, key=lambda item: (item['brand'] or '', item['model'] or ''))

    return render(request, "inventory/workstations-list.html", {
        'workstations': workstations,
        'office_count': len([w for w in workstations if w['usage_type'] == 'office']),
        'lab_count': len([w for w in workstations if w['usage_type'] == 'laboratory']),
        'warehouse_count': len([w for w in workstations if w['usage_type'] == 'warehouse']),
        'serverRoom_count': len([w for w in workstations if w['usage_type'] == 'serverRoom']),
    })


def phone_book(request):
    today = timezone.localdate()
    active_assignments = Assignment.objects.filter(
        assignment_date__lte=today,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).select_related('user')
    phones = Phone.objects.filter(is_active=True).select_related(
        'space__room__floor__building__area__city',
        'common_area__floor__building__area__city',
        'socket',
    ).prefetch_related(
        Prefetch(
            'device_ptr__assignments',
            queryset=active_assignments,
            to_attr='current_assignments',
        )
    )

    entries = []
    users_with_phones = set()
    for phone in phones:
        if phone.space_id:
            space = phone.space
            floor = space.room.floor
            location = (
                f'{floor.building.name} - Floor {floor.floor_number} - '
                f'{space.room.room_code} - {space.name}'
            )
        elif phone.common_area_id:
            common_area = phone.common_area
            floor = common_area.floor
            location = (
                f'{floor.building.name} - Floor {floor.floor_number} - '
                f'{common_area.name}'
            )
        else:
            location = ''
        for assignment in phone.device_ptr.current_assignments:
            user = assignment.user
            if user.status != 'active' or not user.is_active:
                continue
            users_with_phones.add(user.pk)
            entries.append({
                'full_name': f'{user.name} {user.surname}',
                'email': user.email,
                'personal_phone': user.phone,
                'phone_number': phone.phone_number,
                'has_phone': True,
                'socket_code': phone.socket.socket_code if phone.socket_id else '',
                'location': location,
            })

    users_without_phones = User.objects.filter(
        status='active',
        is_active=True,
    ).exclude(pk__in=users_with_phones)
    entries.extend({
        'full_name': f'{user.name} {user.surname}',
        'email': user.email,
        'personal_phone': user.phone,
        'phone_number': None,
        'has_phone': False,
        'socket_code': '',
        'location': '',
    } for user in users_without_phones)
    entries.sort(key=lambda entry: entry['full_name'].casefold())

    return render(request, 'inventory/phone-book.html', {
        'phone_book_entries': entries,
        'page_title': 'Phone Book',
        'page_icon': 'bi bi-journal-text',
        'hide_header_actions': True,
    })


def desktops_list(request):
    # Prefetch active assignments and attached peripherals.
    desktops = DesktopComputer.objects.prefetch_related(
        Prefetch(
            "device_ptr__assignments",
            queryset=Assignment.objects.filter(
                Q(end_date__isnull=True) | Q(end_date__gte=timezone.now().date())
            ).select_related("user"),
        ),
        Prefetch(
            "device_ptr__peripherals",
            queryset=Peripheral.objects.all(),
        ),
    )
    desktops = _filter_by_location(desktops, request, {
        'city': 'space__room__floor__building__area__city_id',
        'area': 'space__room__floor__building__area_id',
        'building': 'space__room__floor__building_id',
        'floor': 'space__room__floor_id',
        'room': 'space__room_id',
        'space': 'space_id',
        'common_area': 'common_area_id',
    })
    return render(request, "inventory/desktops-list.html", {
        "desktops": desktops,
        'office_count':     desktops.filter(usage_type='office').count(),
        'lab_count':        desktops.filter(usage_type='laboratory').count(),
        'warehouse_count':  desktops.filter(usage_type='warehouse').count(),
        'serverRoom_count': desktops.filter(usage_type='serverRoom').count(),
    })

def desktop_detail(request, pk):
    desktop = get_object_or_404(
        DesktopComputer.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
        ).prefetch_related(
            Prefetch(
                "device_ptr__assignments",
                queryset=Assignment.objects.filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=timezone.now().date())
                ).select_related("user"),
            ),
            Prefetch(
                "device_ptr__peripherals",
                queryset=Peripheral.objects.all(),
            ),
        ),
        pk=pk
    )
    return render(request, "inventory/desktop-detail.html", {"desktop": desktop})

def newdesktop(request):
    return handle_create(request, DesktopForm, 'desktops-list')

def updatedesktop(request, pk):
    return handle_update(request, DesktopForm, 'desktops-list', pk)

def deletedesktop(request, pk):
    return handle_delete(request, DesktopComputer, 'desktops-list', pk)


def allInOnes_list(request):
    allinones = AllInOneComputer.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related(
        'device_ptr__assignments__user',
        'device_ptr__peripherals',
    )
    allinones = _filter_by_location(allinones, request, {
        'city': 'space__room__floor__building__area__city_id', 'area': 'space__room__floor__building__area_id',
        'building': 'space__room__floor__building_id', 'floor': 'space__room__floor_id', 'room': 'space__room_id',
        'space': 'space_id', 'common_area': 'common_area_id',
    })
    return render(request, 'inventory/allInOnes-list.html', {
        'allinones': allinones,
        'office_count':     allinones.filter(usage_type='office').count(),
        'lab_count':        allinones.filter(usage_type='laboratory').count(),
        'warehouse_count':  allinones.filter(usage_type='warehouse').count(),
        'serverRoom_count': allinones.filter(usage_type='serverRoom').count(),
    })

def allInOne_detail(request, pk):
    allinone = get_object_or_404(
        AllInOneComputer.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
        ).prefetch_related(
            Prefetch(
                "device_ptr__assignments",
                queryset=Assignment.objects.filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=timezone.now().date())
                ).select_related("user"),
            ),
            Prefetch(
                "device_ptr__peripherals",
                queryset=Peripheral.objects.all(),
            ),
        ),
        pk=pk
    )
    return render(request, "inventory/allInOne-detail.html", {"allinone": allinone})

def hardware_detail(request, model_class, pk, type_label, list_route, update_route, delete_route, specific_fields):
    device = get_object_or_404(
        model_class.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
            'socket__space__room__floor__building',
            'socket__common_area__floor__building',
        ).prefetch_related('device_ptr__assignments__user', 'device_ptr__peripherals'),
        pk=pk,
    )
    fields = [(label, getattr(device, field_name, None)) for field_name, label in specific_fields]
    return render(request, 'inventory/hardware-detail.html', {
        'device': device,
        'type_label': type_label,
        'list_url': reverse(list_route),
        'update_url': reverse(update_route, kwargs={'pk': pk}),
        'delete_url': reverse(delete_route, kwargs={'pk': pk}),
        'specific_fields': fields,
    })

def allInOne_hardware_detail(request, pk):
    return hardware_detail(request, AllInOneComputer, pk, 'All In One', 'allInOnes-list', 'update-allInOne', 'delete-allInOne', [('cpu', 'Processor'), ('ram_gb', 'Memory (GB)'), ('storage_gb', 'Storage (GB)'), ('screen_size', 'Screen Size')])

def laptop_detail(request, pk):
    laptop = get_object_or_404(
        LaptopComputer.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
            'socket__space__room__floor__building',
            'socket__common_area__floor__building',
        ).prefetch_related('device_ptr__assignments__user', 'device_ptr__peripherals'),
        pk=pk,
    )
    return render(request, 'inventory/laptop-detail.html', {'laptop': laptop})

def server_detail(request, pk):
    server = get_object_or_404(
        ServerComputer.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
            'socket__space__room__floor__building',
            'socket__common_area__floor__building',
        ).prefetch_related('device_ptr__assignments__user', 'device_ptr__peripherals'),
        pk=pk,
    )
    return render(request, 'inventory/server-detail.html', {'server': server})

def printer_detail(request, pk):
    printer = get_object_or_404(
        Printer.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
            'socket__space__room__floor__building',
            'socket__common_area__floor__building',
        ).prefetch_related('device_ptr__assignments__user', 'device_ptr__peripherals'),
        pk=pk,
    )
    return render(request, 'inventory/printer-detail.html', {'printer': printer})

def ups_detail(request, pk):
    ups = get_object_or_404(
        Ups.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
            'socket__space__room__floor__building',
            'socket__common_area__floor__building',
        ).prefetch_related('device_ptr__assignments__user', 'device_ptr__peripherals'),
        pk=pk,
    )
    return render(request, 'inventory/ups-detail.html', {'ups': ups})

def switch_detail(request, pk):
    switch = get_object_or_404(
        Switch.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
            'socket__space__room__floor__building',
            'socket__common_area__floor__building',
        ).prefetch_related('device_ptr__assignments__user', 'device_ptr__peripherals'),
        pk=pk,
    )
    return render(request, 'inventory/switch-detail.html', {'switch': switch})

def access_point_detail(request, pk):
    accesspoint = get_object_or_404(
        AccessPoint.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
            'socket__space__room__floor__building',
            'socket__common_area__floor__building',
        ).prefetch_related('device_ptr__assignments__user', 'device_ptr__peripherals'),
        pk=pk,
    )
    return render(request, 'inventory/access-point-detail.html', {'accesspoint': accesspoint})

def phone_detail(request, pk):
    phone = get_object_or_404(
        Phone.objects.select_related(
            'space__room__floor__building__area__city',
            'common_area__floor__building__area__city',
            'socket__space__room__floor__building',
            'socket__common_area__floor__building',
        ).prefetch_related('device_ptr__assignments__user', 'device_ptr__peripherals'),
        pk=pk,
    )
    return render(request, 'inventory/phone-detail.html', {'phone': phone})

def peripheral_detail(request, pk):
    peripheral = get_object_or_404(
        Peripheral.objects.select_related(
            'device__space__room__floor__building__area__city',
            'device__common_area__floor__building__area__city',
            'device__socket__space__room__floor__building',
            'device__socket__common_area__floor__building',
        ),
        pk=pk,
    )
    assigned_device = peripheral.device.get_specific_device()
    return render(request, 'inventory/peripheral-detail.html', {
        'peripheral': peripheral,
        'assigned_device_url': get_search_result_url(assigned_device),
        'list_url': reverse('peripherals-list'),
        'update_url': reverse('update-peripherals', kwargs={'pk': pk}),
        'delete_url': reverse('delete-peripherals', kwargs={'pk': pk}),
    })

def newallInOne(request):
    return handle_create(request, AllInOneForm, 'allInOnes-list')

def updateallInOne(request, pk):
    return handle_update(request, AllInOneForm, 'allInOnes-list', pk)

def deleteallInOne(request, pk):
    return handle_delete(request, AllInOneComputer, 'allInOnes-list', pk)

def laptops_list(request):
    # Load location, assignments, and peripherals efficiently.
    laptops = LaptopComputer.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related(
        'device_ptr__assignments__user',
        'device_ptr__peripherals',
    )
    laptops = _filter_by_location(laptops, request, {
        'city': 'space__room__floor__building__area__city_id', 'area': 'space__room__floor__building__area_id',
        'building': 'space__room__floor__building_id', 'floor': 'space__room__floor_id', 'room': 'space__room_id',
        'space': 'space_id', 'common_area': 'common_area_id',
    })
    return render(request, 'inventory/laptops-list.html', {
        'laptops': laptops,
        'office_count':     laptops.filter(usage_type='office').count(),
        'lab_count':        laptops.filter(usage_type='laboratory').count(),
        'warehouse_count':  laptops.filter(usage_type='warehouse').count(),
        'serverRoom_count': laptops.filter(usage_type='serverRoom').count(),
    })


def newLaptop(request):
    return handle_create(request, LaptopForm, 'laptops-list')

def updateLaptop(request, pk):
    return handle_update(request, LaptopForm, 'laptops-list', pk)

def deleteLaptop(request, pk):
    return handle_delete(request,LaptopComputer, 'laptops-list', pk)


def servers_list(request):
    servers = ServerComputer.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related('device_ptr__assignments__user')
    servers = _filter_by_location(servers, request, {
        'city': 'space__room__floor__building__area__city_id', 'area': 'space__room__floor__building__area_id',
        'building': 'space__room__floor__building_id', 'floor': 'space__room__floor_id', 'room': 'space__room_id',
        'space': 'space_id', 'common_area': 'common_area_id',
    })
    return render(request, 'inventory/servers-list.html', {
        'servers': servers,
        'office_count':     servers.filter(usage_type='office').count(),
        'lab_count':        servers.filter(usage_type='laboratory').count(),
        'warehouse_count':  servers.filter(usage_type='warehouse').count(),
        'serverRoom_count': servers.filter(usage_type='serverRoom').count(),
    })
def newServer(request):
    return handle_create(request, ServerForm, 'servers-list')

def updateServer(request, pk):
    return handle_update(request, ServerForm, 'servers-list', pk)

def deleteServer(request, pk):
    return handle_delete(request, ServerComputer, 'servers-list', pk)


def printers_list(request):
    printers = Printer.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related('device_ptr__assignments__user')
    printers = _filter_by_location(printers, request, {
        'city': 'space__room__floor__building__area__city_id', 'area': 'space__room__floor__building__area_id',
        'building': 'space__room__floor__building_id', 'floor': 'space__room__floor_id', 'room': 'space__room_id',
        'space': 'space_id', 'common_area': 'common_area_id',
    })
    return render(request, 'inventory/printers-list.html', {
        'printers': printers,
        'office_count':     printers.filter(usage_type='office').count(),
        'lab_count':        printers.filter(usage_type='laboratory').count(),
        'warehouse_count':  printers.filter(usage_type='warehouse').count(),
        'serverRoom_count': printers.filter(usage_type='serverRoom').count(),
    })
def newPrinter(request):
    return handle_create(request, PrinterForm, 'printers-list')

def updatePrinter(request, pk):
    return handle_update(request, PrinterForm, 'printers-list', pk)

def deletePrinter(request, pk):
    return handle_delete(request, Printer, 'printers-list', pk)



def upses_list(request):
    upses = Ups.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related('device_ptr__assignments__user')
    upses = _filter_by_location(upses, request, {
        'city': 'space__room__floor__building__area__city_id', 'area': 'space__room__floor__building__area_id',
        'building': 'space__room__floor__building_id', 'floor': 'space__room__floor_id', 'room': 'space__room_id',
        'space': 'space_id', 'common_area': 'common_area_id',
    })
    return render(request, 'inventory/upses-list.html', {
        'upses': upses,
        'office_count':     upses.filter(usage_type='office').count(),
        'lab_count':        upses.filter(usage_type='laboratory').count(),
        'warehouse_count':  upses.filter(usage_type='warehouse').count(),
        'serverRoom_count': upses.filter(usage_type='serverRoom').count(),
    })

def newUpses(request):
    return handle_create(request, UpsForm, 'upses-list')

def updateUpses(request, pk):
    return handle_update(request, UpsForm, 'upses-list', pk)

def deleteUpses(request, pk):
    return handle_delete(request, Ups, 'upses-list', pk)


def switches_list(request):
    switches = Switch.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related('device_ptr__assignments__user')
    switches = _filter_by_location(switches, request, {
        'city': 'space__room__floor__building__area__city_id', 'area': 'space__room__floor__building__area_id',
        'building': 'space__room__floor__building_id', 'floor': 'space__room__floor_id', 'room': 'space__room_id',
        'space': 'space_id', 'common_area': 'common_area_id',
    })
    return render(request, 'inventory/switches-list.html', {
        'switches': switches,
        'office_count':     switches.filter(usage_type='office').count(),
        'lab_count':        switches.filter(usage_type='laboratory').count(),
        'warehouse_count':  switches.filter(usage_type='warehouse').count(),
        'serverRoom_count': switches.filter(usage_type='serverRoom').count(),
    })

def newSwitches(request):
    return handle_create(request, SwitchForm, 'switches-list')

def updateSwitches(request, pk):
    return handle_update(request, SwitchForm, 'switches-list', pk)

def deleteSwitches(request, pk):
    return handle_delete(request, Switch, 'switches-list', pk)


def access_points_list(request):
    accesspoints = AccessPoint.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related('device_ptr__assignments__user')
    accesspoints = _filter_by_location(accesspoints, request, {
        'city': 'space__room__floor__building__area__city_id', 'area': 'space__room__floor__building__area_id',
        'building': 'space__room__floor__building_id', 'floor': 'space__room__floor_id', 'room': 'space__room_id',
        'space': 'space_id', 'common_area': 'common_area_id',
    })
    return render(request, 'inventory/access-points-list.html', {
        'accesspoints': accesspoints,
        'office_count':     accesspoints.filter(usage_type='office').count(),
        'lab_count':        accesspoints.filter(usage_type='laboratory').count(),
        'warehouse_count':  accesspoints.filter(usage_type='warehouse').count(),
        'serverRoom_count': accesspoints.filter(usage_type='serverRoom').count(),
    })
def newAccessPoints(request):
    return handle_create(request, AccessPointForm, 'access-points-list')

def updateAccessPoints(request, pk):
    return handle_update(request, AccessPointForm, 'access-points-list', pk)

def deleteAccessPoints(request, pk):
    return handle_delete(request, AccessPoint, 'access-points-list', pk)


def phones_list(request):
    phones = Phone.objects.select_related(
        'space__room__floor__building__area__city'
    ).prefetch_related('device_ptr__assignments__user')
    phones = _filter_by_location(phones, request, {
        'city': 'space__room__floor__building__area__city_id', 'area': 'space__room__floor__building__area_id',
        'building': 'space__room__floor__building_id', 'floor': 'space__room__floor_id', 'room': 'space__room_id',
        'space': 'space_id', 'common_area': 'common_area_id',
    })
    return render(request, 'inventory/phones-list.html', {
        'phones': phones,
        'office_count':     phones.filter(usage_type='office').count(),
        'lab_count':        phones.filter(usage_type='laboratory').count(),
        'warehouse_count':  phones.filter(usage_type='warehouse').count(),
        'serverRoom_count': phones.filter(usage_type='serverRoom').count(),
    })
def newPhones(request):
    return handle_create(request, PhoneForm, 'phones-list')

def updatePhones(request, pk):
    return handle_update(request, PhoneForm, 'phones-list', pk)

def deletePhones(request, pk):
    return handle_delete(request, Phone, 'phones-list', pk)



def peripherals_list(request):
    peripherals = Peripheral.objects.select_related(
        'device__space__room__floor__building__area__city'
    )
    peripherals = _filter_by_location(peripherals, request, {
        'city': 'device__space__room__floor__building__area__city_id', 'area': 'device__space__room__floor__building__area_id',
        'building': 'device__space__room__floor__building_id', 'floor': 'device__space__room__floor_id',
        'room': 'device__space__room_id', 'space': 'device__space_id', 'common_area': 'device__common_area_id',
    })
    return render(request, 'inventory/peripherals-list.html', {'peripherals': peripherals})

def newPeripherals(request):
    return handle_create(request, PeripheralForm, 'peripherals-list')

def updatePeripherals(request, pk):
    return handle_update(request, PeripheralForm, 'peripherals-list', pk)

def deletePeripherals(request, pk):
    return handle_delete(request, Peripheral, 'peripherals-list', pk)





# Utility views.

def _export_model_name(model_name):
    aliases = {
        'general-directorate': 'generaldirectorate',
        'general-directorates': 'generaldirectorate',
        'directorate': 'directorate',
        'department': 'department',
        'office': 'office',
        'city': 'city',
        'area': 'area',
        'building': 'building',
        'floor': 'floor',
        'common-area': 'commonarea',
        'commonarea': 'commonarea',
        'common-areas': 'commonarea',
        'room': 'room',
        'space': 'space',
        'socket': 'socket',
        'assignment': 'assignment',
        'user': 'user',
        'allinonecomputer': 'allinonecomputer',
        'all-in-one': 'allinonecomputer',
        'allinone': 'allinonecomputer',
        'desktopcomputer': 'desktopcomputer',
        'desktop': 'desktopcomputer',
        'laptopcomputer': 'laptopcomputer',
        'laptop': 'laptopcomputer',
        'servercomputer': 'servercomputer',
        'server': 'servercomputer',
        'printer': 'printer',
        'ups': 'ups',
        'switch': 'switch',
        'accesspoint': 'accesspoint',
        'access-point': 'accesspoint',
        'phone': 'phone',
        'peripheral': 'peripheral',
        'device': 'device',
    }
    normalized = model_name.strip().lower().replace(' ', '-')
    return aliases.get(normalized, normalized)


def _export_model_queryset(model_name):
    normalized = _export_model_name(model_name)
    try:
        model = apps.get_model('nodes', normalized)
    except LookupError:
        model = apps.get_model('nodes', normalized.replace('-', ''))
    if model is None:
        raise ValueError(f'Unknown export model: {model_name}')
    return model.objects.all()


def _export_fields(model):
    return [field for field in model._meta.concrete_fields if not field.auto_created]


def _export_value(record, field):
    value = getattr(record, field.name, None)
    if field.choices:
        return getattr(record, f'get_{field.name}_display')()
    if value is None:
        return ''
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


class _DetailTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._cells = []
        self._buffer = []
        self._in_row = False
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self._cells = []
            self._in_row = True
        elif self._in_row and tag in {'th', 'td'}:
            self._buffer = []
            self._in_cell = True

    def handle_data(self, data):
        if self._in_cell:
            self._buffer.append(data)

    def handle_endtag(self, tag):
        if tag in {'th', 'td'} and self._in_cell:
            self._cells.append(' '.join(''.join(self._buffer).split()))
            self._buffer = []
            self._in_cell = False
        elif tag == 'tr' and self._in_row:
            if len(self._cells) >= 2 and self._cells[0]:
                self.rows.append((self._cells[0], ' '.join(self._cells[1:])))
            self._cells = []
            self._in_row = False


DETAIL_EXPORT_ROUTES = {
    'city': 'city-detail',
    'area': 'area-detail',
    'building': 'building-detail',
    'floor': 'floor-detail',
    'commonarea': 'common-area-detail',
    'room': 'room-detail',
    'space': 'space-detail',
    'socket': 'socket-detail',
    'generaldirectorate': 'general-directorate-detail',
    'directorate': 'directorate-detail',
    'department': 'department-detail',
    'office': 'office-detail',
    'user': 'user-detail',
    'assignment': 'assignment-detail',
    'desktopcomputer': 'desktop-detail',
    'allinonecomputer': 'allInOne-detail',
    'laptopcomputer': 'laptop-detail',
    'servercomputer': 'server-detail',
    'printer': 'printer-detail',
    'ups': 'ups-detail',
    'switch': 'switch-detail',
    'accesspoint': 'access-point-detail',
    'phone': 'phone-detail',
    'peripheral': 'peripheral-detail',
}


def _detail_page_export_data(model_name, pk):
    normalized = _export_model_name(model_name)
    route_name = DETAIL_EXPORT_ROUTES.get(normalized)
    if not route_name:
        return None

    detail_path = reverse(route_name, kwargs={'pk': pk})
    detail_request = RequestFactory().get(detail_path)
    detail_request.resolver_match = resolve(detail_path)
    response = detail_request.resolver_match.func(detail_request, pk=pk)
    if response.status_code != 200:
        return None

    parser = _DetailTableParser()
    parser.feed(response.content.decode(response.charset or 'utf-8'))
    if not parser.rows:
        return None

    queryset = _export_model_queryset(model_name).filter(pk=pk)
    record = queryset.first()
    model = queryset.model
    return {
        'model': model_name,
        'title': model._meta.verbose_name.title(),
        'count': 1,
        'records': [{
            'title': str(record) if record is not None else model._meta.verbose_name.title(),
            'fields': [
                {'title': title, 'name': re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_'), 'value': value}
                for title, value in parser.rows
            ],
        }],
    }


def _export_records_data(model_name, queryset):
    model = queryset.model
    fields = _export_fields(model)
    records = []
    for record in queryset:
        records.append({
            'title': str(record),
            'fields': [
                {
                    'title': field.verbose_name.title(),
                    'name': field.name,
                    'value': _export_value(record, field),
                }
                for field in fields
            ],
        })
    return {
        'model': model_name,
        'title': model._meta.verbose_name.title(),
        'count': len(records),
        'records': records,
    }


def _device_statistics_export_data():
    active_assignments = Assignment.objects.filter(
        Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate())
    )
    total_devices = Device.objects.count()
    assigned_devices = active_assignments.values('device_id').distinct().count()
    pingable_ips = list(
        Device.objects.exclude(ip_address__isnull=True)
        .exclude(ip_address='')
        .values_list('ip_address', flat=True)
    )
    ping_worker_count = min(32, max(1, len(pingable_ips)))
    with ThreadPoolExecutor(max_workers=ping_worker_count) as executor:
        ping_statuses = list(executor.map(_run_ping, pingable_ips))
    reachable_count = sum(status[0] for status in ping_statuses)
    unreachable_count = len(ping_statuses) - reachable_count

    sections = [
        ('Spatial inventory', [('Cities', City.objects.count()), ('Areas', Area.objects.count()), ('Buildings', Building.objects.count()), ('Floors', Floor.objects.count()), ('Rooms', Room.objects.count()), ('Spaces', Space.objects.count()), ('Common areas', CommonArea.objects.count()), ('Sockets', Socket.objects.count())]),
        ('Organization', [('General directorates', GeneralDirectorate.objects.count()), ('Directorates', Directorate.objects.count()), ('Departments', Department.objects.count()), ('Offices', Office.objects.count()), ('Users', User.objects.count())]),
        ('Assignments and inventory', [('Assignments', Assignment.objects.count()), ('Peripherals', Peripheral.objects.count()), ('All devices', Device.objects.count())]),
        ('Devices by type', [('Desktops', DesktopComputer.objects.count()), ('All-In-Ones', AllInOneComputer.objects.count()), ('Laptops', LaptopComputer.objects.count()), ('Servers', ServerComputer.objects.count()), ('Printers', Printer.objects.count()), ('UPS Units', Ups.objects.count()), ('Switches', Switch.objects.count()), ('Access Points', AccessPoint.objects.count()), ('Phones', Phone.objects.count())]),
        ('Network ping', [('Registered IP addresses', len(pingable_ips)), ('Reachable devices', reachable_count), ('Failed devices', unreachable_count)]),
    ]
    records = [{
        'title': 'Summary',
        'fields': [
            {'title': 'Total devices', 'name': 'total_devices', 'value': str(total_devices)},
            {'title': 'Assigned devices', 'name': 'assigned_devices', 'value': str(assigned_devices)},
            {'title': 'Unassigned devices', 'name': 'unassigned_devices', 'value': str(total_devices - assigned_devices)},
        ],
    }]
    records.extend({
        'title': title,
        'fields': [{'title': label, 'name': label.lower().replace(' ', '_'), 'value': str(count)} for label, count in entries],
    } for title, entries in sections)
    records.extend([
        {
            'title': 'Pie chart: Devices by type',
            'fields': [{'title': label, 'name': label.lower().replace(' ', '_'), 'value': str(count)} for label, count in sections[3][1]],
            'chart': sections[3][1],
        },
        {
            'title': 'Pie chart: Assignment status',
            'fields': [
                {'title': 'Assigned devices', 'name': 'assigned_devices', 'value': str(assigned_devices)},
                {'title': 'Unassigned devices', 'name': 'unassigned_devices', 'value': str(total_devices - assigned_devices)},
            ],
            'chart': [('Assigned devices', assigned_devices), ('Unassigned devices', total_devices - assigned_devices)],
        },
        {
            'title': 'Pie chart: Ping status',
            'fields': [
                {'title': 'Reachable', 'name': 'reachable', 'value': str(reachable_count)},
                {'title': 'Failed', 'name': 'failed', 'value': str(unreachable_count)},
            ],
            'chart': [('Reachable', reachable_count), ('Failed', unreachable_count)],
        },
    ])
    return {'model': 'device-statistics', 'title': 'Statistics', 'count': len(records), 'records': records}


def export_device_statistics(request, format_name):
    data = _device_statistics_export_data()
    format_name = format_name.lower()
    if format_name == 'json':
        response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=2), content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="statistics_export.json"'
        return response
    if format_name == 'docx':
        response = HttpResponse(_build_docx_bytes(data), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = 'attachment; filename="statistics_export.docx"'
        return response
    if format_name == 'pdf':
        response = HttpResponse(_build_pdf_bytes(data), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="statistics_report.pdf"'
        return response
    return HttpResponse('Unsupported export format. Use docx or json.', status=400)


def _build_pdf_bytes(data):
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.4 * inch,
        leftMargin=0.4 * inch,
        topMargin=0.35 * inch,
        bottomMargin=0.35 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ReportTitle', parent=styles['Title'], fontSize=22, textColor=colors.white, spaceAfter=2)
    subtitle_style = ParagraphStyle('ReportSubtitle', parent=styles['BodyText'], fontSize=9, textColor=colors.white)
    metric_style = ParagraphStyle('MetricValue', parent=styles['Title'], fontSize=24, textColor=colors.HexColor('#123b76'), alignment=1, spaceAfter=0)
    summary_label_style = ParagraphStyle('SummaryLabel', parent=styles['BodyText'], fontSize=10, leading=12, textColor=colors.HexColor('#123b76'))
    section_style = ParagraphStyle('SectionTitle', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#123b76'), spaceBefore=6, spaceAfter=4)
    chart_title_style = ParagraphStyle('ChartTitle', parent=section_style, leftIndent=10, spaceBefore=0)
    body_style = ParagraphStyle('Body', parent=styles['BodyText'], fontSize=8.5, leading=10)
    header = Table([[Paragraph('Statistics', title_style)]], colWidths=[10.2 * inch])
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0d6efd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
    ]))
    story = [header, Spacer(1, 8)]

    records = data['records']
    summary = next(record for record in records if record['title'] == 'Summary')
    summary_cells = [[Paragraph(field['title'], summary_label_style), Paragraph(field['value'] or '-', metric_style)] for field in summary['fields']]
    summary_table = Table([summary_cells], colWidths=[2.55 * inch] * len(summary_cells))
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eef4fc')),
        ('BOX', (0, 0), (-1, -1), 0.7, colors.HexColor('#8fb2df')),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#c9d9ed')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.extend([summary_table, Spacer(1, 8)])

    charts = [record for record in records if record.get('chart')]
    chart_cells = []
    for chart in charts:
        chart_drawing = _pdf_pie_drawing(chart['chart'], size=235)
        chart_cells.append([Paragraph(chart['title'].replace('Pie chart: ', ''), chart_title_style), chart_drawing])
    if chart_cells:
        chart_table = Table([chart_cells], colWidths=[3.4 * inch] * len(chart_cells))
        chart_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#d6e0ed')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d6e0ed')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.extend([chart_table, Spacer(1, 8)])

    section_records = [record for record in records if record['title'] != 'Summary' and not record.get('chart')]
    section_columns = [[], []]
    for index, record in enumerate(section_records):
        rows = [[Paragraph(field['title'], body_style), Paragraph(field['value'] or '-', body_style)] for field in record['fields']]
        table = Table(rows, colWidths=[3.75 * inch, 0.85 * inch])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#d4deeb')),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#0d6efd')),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        section_columns[index % 2].extend([
            Paragraph(record['title'], section_style),
            table,
            Spacer(1, 8),
        ])

    sections_table = Table([[section_columns[0], section_columns[1]]], colWidths=[5.1 * inch, 5.1 * inch], hAlign='LEFT')
    sections_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sections_table)
    document.build(story, onFirstPage=_pdf_footer, onLaterPages=_pdf_footer)
    return buffer.getvalue()


def _pdf_footer(canvas, document):
    generated_at = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#6c757d'))
    canvas.drawString(document.leftMargin, 0.18 * inch, f'Report generated: {generated_at}')
    canvas.restoreState()


def _pdf_pie_drawing(entries, size=150):
    colorset = [
        colors.HexColor('#0d6efd'), colors.HexColor('#198754'), colors.HexColor('#ffc107'),
        colors.HexColor('#dc3545'), colors.HexColor('#6f42c1'), colors.HexColor('#0dcaf0'),
        colors.HexColor('#fd7e14'), colors.HexColor('#20c997'), colors.HexColor('#6c757d'),
    ]
    values = [max(0, value) for _, value in entries]
    total = sum(values)
    labels = [f'{round((value / total) * 100)}%' if total else '0%' for value in values]
    drawing = Drawing(size, size)
    pie = Pie()
    pie.x = 10
    pie.y = 10
    pie.width = size - 20
    pie.height = size - 20
    pie.data = values or [1]
    pie.labels = labels or ['0%']
    pie.sideLabels = False
    pie.simpleLabels = True
    pie.sameRadii = True
    pie.startAngle = 90
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 1
    for index in range(len(pie.data)):
        pie.slices[index].fillColor = colorset[index % len(colorset)]
        pie.slices[index].fontSize = 8
        pie.slices[index].fontColor = colors.white
    drawing.add(pie)
    if total:
        angle = math.pi / 2
        center = size / 2
        label_radius = (size - 20) * 0.28
        for value, label in zip(values, labels):
            sweep = (value / total) * math.tau
            midpoint = angle - (sweep / 2)
            x = center + math.cos(midpoint) * label_radius
            y = center + math.sin(midpoint) * label_radius
            drawing.add(String(x, y, label, fontName='Helvetica-Bold', fontSize=9, fillColor=colors.white, textAnchor='middle'))
            angle -= sweep
    return drawing


def _pie_png_bytes(entries, size=420):
    colors = [
        (13, 110, 253), (25, 135, 84), (255, 193, 7), (220, 53, 69),
        (111, 66, 193), (13, 202, 240), (253, 126, 20), (32, 201, 151),
        (108, 117, 125),
    ]
    total = sum(max(0, value) for _, value in entries)
    center = size / 2
    radius = size * 0.42
    pixels = bytearray()
    angle = -math.pi / 2
    boundaries = []
    if total:
        for index, (_, value) in enumerate(entries):
            next_angle = angle + (max(0, value) / total) * math.tau
            boundaries.append((angle, next_angle, colors[index % len(colors)]))
            angle = next_angle

    for y in range(size):
        pixels.append(0)
        for x in range(size):
            distance = math.hypot(x - center, y - center)
            color = (245, 247, 250)
            if distance <= radius and boundaries:
                point_angle = math.atan2(y - center, x - center)
                if point_angle < -math.pi / 2:
                    point_angle += math.tau
                for start, end, candidate in boundaries:
                    adjusted = point_angle
                    if adjusted < start:
                        adjusted += math.tau
                    if start <= adjusted < end:
                        color = candidate
                        break
            pixels.extend((*color, 255))

    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)

    raw = zlib.compress(bytes(pixels), 9)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)) + chunk(b'IDAT', raw) + chunk(b'IEND', b'')


def _docx_image_paragraph(relationship_id, extent=4572000):
    return (
        '<w:p><w:r><w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<wp:extent cx="{extent}" cy="{extent}"/><wp:docPr id="1" name="Pie chart"/>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="pie.png"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="' + relationship_id + '" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{extent}" cy="{extent}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
    )


def _build_docx_bytes(data):
    def paragraph(text, bold=False):
        return f'<w:p><w:r><w:rPr>{"<w:b/>" if bold else ""}</w:rPr><w:t>{html.escape(text)}</w:t></w:r></w:p>'

    def table_spacing():
        return '<w:p><w:pPr><w:spacing w:after="180"/></w:pPr></w:p>'

    def header_table(title):
        return (
            '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>'
            '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
            '</w:tblPr><w:tr>'
            '<w:tc><w:tcPr><w:shd w:fill="0D6EFD"/></w:tcPr>'
            + '<w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="32"/></w:rPr><w:t>' + html.escape(title) + '</w:t></w:r></w:p>'
            + '</w:tc></w:tr></w:tbl>'
        )

    def table(rows):
        border = '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="B7C9E2"/><w:left w:val="single" w:sz="4" w:color="B7C9E2"/><w:bottom w:val="single" w:sz="4" w:color="B7C9E2"/><w:right w:val="single" w:sz="4" w:color="B7C9E2"/><w:insideH w:val="single" w:sz="4" w:color="D9E2F3"/><w:insideV w:val="single" w:sz="4" w:color="D9E2F3"/></w:tblBorders>'
        body = []
        for row_index, row in enumerate(rows):
            cells = []
            for value in row:
                shading = '<w:tcPr><w:shd w:fill="D9E8FB"/></w:tcPr>' if row_index == 0 else ''
                cells.append(f'<w:tc>{shading}{paragraph(str(value), row_index == 0)}</w:tc>')
            body.append('<w:tr>' + ''.join(cells) + '</w:tr>')
        return '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>' + border + '</w:tblPr>' + ''.join(body) + '</w:tbl>'

    chart_records = [record for record in data['records'] if record.get('chart')]
    regular_records = [record for record in data['records'] if not record.get('chart')]
    paragraphs = [header_table(data['title'])]
    for record in regular_records:
        paragraphs.append(table([['Field', 'Value'], ['Record', record['title']]] + [
            [field['title'], field['value'] or '-'] for field in record['fields']
        ]))
        paragraphs.append(table_spacing())

    if chart_records:
        paragraphs.append(paragraph('Charts', True))
        chart_cells = []
        for image_index, record in enumerate(chart_records, start=1):
            chart_cells.append(
                '<w:tc><w:tcPr><w:tcW w:w="3000" w:type="dxa"/></w:tcPr>'
                + paragraph(record['title'].replace('Pie chart: ', ''), True)
                + _docx_image_paragraph(f'rId{image_index + 1}', 2600000)
                + '</w:tc>'
            )
        paragraphs.append('<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/></w:tblPr><w:tr>' + ''.join(chart_cells) + '</w:tr></w:tbl>')

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{"".join(paragraphs)}<w:sectPr>'
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
        '</w:sectPr></w:body></w:document>'
    )
    image_records = [record for record in data['records'] if record.get('chart')]
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        + ''.join(f'<Override PartName="/word/media/pie{index}.png" ContentType="image/png"/>' for index, _ in enumerate(image_records, start=1))
        + '</Types>'
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    )
    document_relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + ''.join(f'<Relationship Id="rId{index + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/pie{index}.png"/>' for index, _ in enumerate(image_records, start=1))
        + '</Relationships>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', content_types)
        archive.writestr('_rels/.rels', relationships)
        archive.writestr('word/document.xml', document_xml)
        archive.writestr('word/_rels/document.xml.rels', document_relationships)
        for index, record in enumerate(image_records, start=1):
            archive.writestr(f'word/media/pie{index}.png', _pie_png_bytes(record['chart']))
    return buffer.getvalue()


def export_records(request, model_name, format_name, pk=None):
    try:
        queryset = _export_model_queryset(model_name)
    except ValueError:
        return HttpResponse('Unsupported model for export.', status=400)

    if pk is not None:
        queryset = queryset.filter(pk=pk)
        if not queryset.exists():
            return HttpResponse('Record not found.', status=404)

    format_name = format_name.lower()
    data = _detail_page_export_data(model_name, pk) if pk is not None else None
    data = data or _export_records_data(model_name, queryset)
    if format_name == 'json':
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type='application/json; charset=utf-8',
        )
        response['Content-Disposition'] = f'attachment; filename="{model_name}_export.json"'
        return response
    if format_name == 'docx':
        response = HttpResponse(
            _build_docx_bytes(data),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = f'attachment; filename="{model_name}_export.docx"'
        return response
    return HttpResponse('Unsupported export format. Use docx or json.', status=400)


def queries_list(request):
    return render(request, "inventory/queries-list.html")


def map(request):
    return render(request, "inventory/map.html")


def _run_ping(ip):
    """Run one fast platform-appropriate ping."""
    is_windows = platform.system().lower() == "windows"
    param = "-n" if is_windows else "-c"
    command = ["ping", param, "1"]
    command.extend(["-w", "1000"] if is_windows else ["-W", "1"])
    command.append(ip)
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)

    return result.returncode == 0, result.stdout or result.stderr


def _single_ping_context(
    ip,
    output,
    reachable,
    return_url,
    brand="",
    model="",
    registration_code="",
    device=None,
    assigned_users=None,
    location="",
    device_detail_url=None,
):
    if ip:
        status_label = "Reachable" if reachable else "Not reachable"
        status_class = "success" if reachable else "danger"
        status_icon = "bi-check-circle" if reachable else "bi-x-circle"
        subtitle = f"Network diagnostic - {ip}"
    else:
        status_label = "No IP address"
        status_class = "warning"
        status_icon = "bi-exclamation-circle"
        subtitle = "Network diagnostic"

    return {
        "ip": ip,
        "reachable": reachable,
        "output": output,
        "return_url": return_url,
        "device_detail_url": device_detail_url or return_url,
        "page_subtitle": subtitle,
        "page_status_label": status_label,
        "page_status_class": status_class,
        "page_status_icon": status_icon,
        "device_brand": brand,
        "device_model": model,
        "registration_code": registration_code,
        "device": device,
        "assigned_users": assigned_users or [],
        "location": location,
    }


def ping_devices(request):
    """Ping one device or all registered devices based on the current URL."""
    if request.resolver_match.url_name == "ping-all-devices":
        status_filter = (request.GET.get('status') or '').strip().lower()
        if status_filter not in {'reachable', 'failed'}:
            status_filter = ''

        detail_routes = {
            "DesktopComputer": "desktop-detail",
            "AllInOneComputer": "allInOne-detail",
            "LaptopComputer": "laptop-detail",
            "ServerComputer": "server-detail",
            "Printer": "printer-detail",
            "Ups": "ups-detail",
            "Switch": "switch-detail",
            "AccessPoint": "access-point-detail",
            "Phone": "phone-detail",
        }
        active_assignments = Assignment.objects.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate())
        ).select_related("user")
        devices = Device.objects.select_related(
            "space__room__floor__building__area__city",
            "common_area__floor__building__area__city",
        ).prefetch_related(
            Prefetch("assignments", queryset=active_assignments, to_attr="active_assignments")
        ).exclude(ip_address__isnull=True).exclude(ip_address="").order_by("ip_address")

        pending_results = []
        for device in devices:
            specific = device.get_specific_device()
            route_name = detail_routes.get(specific.__class__.__name__, "device-detail")
            assignments = getattr(device, "active_assignments", [])
            if device.space:
                location = " / ".join([
                    device.space.room.floor.building.area.city.name,
                    device.space.room.floor.building.name,
                    f"Floor {device.space.room.floor.floor_number}",
                    device.space.room.room_code,
                    device.space.name,
                ])
            elif device.common_area:
                location = " / ".join([
                    device.common_area.floor.building.area.city.name,
                    device.common_area.floor.building.name,
                    f"Floor {device.common_area.floor.floor_number}",
                    device.common_area.name,
                ])
            else:
                location = "Unassigned location"

            pending_results.append({
                "device": specific,
                "ip": device.ip_address,
                "brand": device.brand,
                "model": device.model,
                "registration_code": device.registration_code,
                "assigned_users": [str(assignment.user) for assignment in assignments],
                "location": location,
                "detail_url": reverse(route_name, kwargs={"pk": device.pk}),
            })

        worker_count = min(32, max(1, len(pending_results)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            ping_results = executor.map(
                _run_ping,
                [result["ip"] for result in pending_results],
            )

        results = []
        for result, (reachable, output) in zip(pending_results, ping_results):
            result["reachable"] = reachable
            result["output"] = output
            results.append(result)

        registered_count = len(results)
        reachable_count = sum(result["reachable"] for result in results)
        unreachable_count = registered_count - reachable_count
        if status_filter:
            expected_reachability = status_filter == 'reachable'
            results = [
                result for result in results
                if result['reachable'] == expected_reachability
            ]

        return render(request, "inventory/ping-all-devices.html", {
            "results": results,
            "registered_count": registered_count,
            "reachable_count": reachable_count,
            "unreachable_count": unreachable_count,
            "status_filter_label": status_filter,
            "status_filter_title": f'{status_filter.title()} devices' if status_filter else '',
            "page_heading": f'{status_filter.title()} devices' if status_filter else "Ping all devices",
            "page_subtitle": "Network diagnostic for registered IP addresses",
            "page_icon": "bi bi-broadcast-pin",
            "hide_header_actions": True,
            "header_action_url": reverse("ping-all-devices") + (f'?status={status_filter}' if status_filter else ''),
            "header_action_label": "Run again",
            "header_action_icon": "bi-arrow-repeat",
        })

    ip = (request.GET.get("ip") or request.GET.get("ip_address") or "").strip()
    device_brand = request.GET.get("brand", "").strip()
    device_model = request.GET.get("model", "").strip()
    registration_code = request.GET.get("registration_code", "").strip()
    return_url = (request.GET.get("return_url") or "").strip()
    if return_url and return_url.startswith("/"):
        allowed_return_url = return_url
    elif return_url and url_has_allowed_host_and_scheme(return_url, allowed_hosts={request.get_host()}):
        allowed_return_url = return_url
    else:
        allowed_return_url = reverse("devices-list")
    return_url = allowed_return_url

    if not ip:
        context = _single_ping_context(
            None,
            "No IP provided.",
            None,
            return_url,
            device_brand,
            device_model,
            registration_code,
        )
        return render(request, "inventory/ping_result.html", context)

    active_assignments = Assignment.objects.filter(
        Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate())
    ).select_related("user")
    device = Device.objects.select_related(
        "space__room__floor__building__area__city",
        "common_area__floor__building__area__city",
    ).prefetch_related(
        Prefetch("assignments", queryset=active_assignments, to_attr="active_assignments")
    ).filter(ip_address=ip).first()

    assigned_users = []
    location = ""
    device_detail_url = return_url
    if device:
        base_device = device
        specific_device = device.get_specific_device()
        device_brand = device.brand
        device_model = device.model or ""
        registration_code = device.registration_code or ""
        device = specific_device
        assigned_users = [str(assignment.user) for assignment in base_device.active_assignments]
        route_name = {
            "DesktopComputer": "desktop-detail",
            "AllInOneComputer": "allInOne-detail",
            "LaptopComputer": "laptop-detail",
            "ServerComputer": "server-detail",
            "Printer": "printer-detail",
            "Ups": "ups-detail",
            "Switch": "switch-detail",
            "AccessPoint": "access-point-detail",
            "Phone": "phone-detail",
        }.get(device.__class__.__name__)
        if route_name:
            device_detail_url = reverse(route_name, kwargs={"pk": device.pk})
        if device.space:
            location = " / ".join([
                device.space.room.floor.building.area.city.name,
                device.space.room.floor.building.name,
                f"Floor {device.space.room.floor.floor_number}",
                device.space.room.room_code,
                device.space.name,
            ])
        elif device.common_area:
            location = " / ".join([
                device.common_area.floor.building.area.city.name,
                device.common_area.floor.building.name,
                f"Floor {device.common_area.floor.floor_number}",
                device.common_area.name,
            ])

    reachable, output = _run_ping(ip)
    context = _single_ping_context(
        ip,
        output,
        reachable,
        return_url,
        device_brand,
        device_model,
        registration_code,
        device,
        assigned_users,
        location,
        device_detail_url,
    )
    return render(request, "inventory/ping_result.html", context)


from django.shortcuts import render
from watson import search as watson  # Explicitly import search engine backend


def get_search_result_url(obj):
    pk = getattr(obj, "pk", None)
    if pk is None:
        return None

    detail_routes = {
        "city": "city-detail",
        "area": "area-detail",
        "building": "building-detail",
        "floor": "floor-detail",
        "commonarea": "common-area-detail",
        "room": "room-detail",
        "space": "space-detail",
        "socket": "socket-detail",
        "generaldirectorate": "general-directorate-detail",
        "directorate": "directorate-detail",
        "department": "department-detail",
        "office": "office-detail",
        "user": "user-detail",
        "device": "device-detail",
        "desktopcomputer": "desktop-detail",
        "allinonecomputer": "allInOne-detail",
        "laptopcomputer": "laptop-detail",
        "servercomputer": "server-detail",
        "printer": "printer-detail",
        "ups": "ups-detail",
        "switch": "switch-detail",
        "accesspoint": "access-point-detail",
        "phone": "phone-detail",
        "peripheral": "peripheral-detail",
        "assignment": "assignment-detail",
    }
    route_name = detail_routes.get(obj._meta.model_name)
    if route_name:
        return reverse(route_name, kwargs={"pk": pk})

    return reverse(
        "record-detail",
        kwargs={
            "app_label": obj._meta.app_label,
            "model_name": obj._meta.model_name,
            "pk": pk,
        },
    )


def get_search_result_title(obj, query):
    normalized_query = query.casefold()
    field_matches = []
    seen_matches = set()

    sources = [obj]
    for field in obj._meta.fields:
        if field.is_relation:
            related_object = getattr(obj, field.name, None)
            if related_object is not None:
                sources.append(related_object)

    for source in sources:
        source_fields = {
            field.name: field
            for field in source._meta.fields
            if field.name != "id" and not field.is_relation
        }
        name_fields = [source_fields.get("name"), source_fields.get("surname")]
        name_values = [
            field.value_from_object(source)
            for field in name_fields
            if field is not None and field.value_from_object(source)
        ]
        name_matches = any(
            normalized_query in str(value).casefold() for value in name_values
        )

        for field in source._meta.fields:
            if field.name == "id" or field.is_relation:
                continue

            value = field.value_from_object(source)
            if value in (None, ""):
                continue

            display_value = str(value)
            is_serial_field = field.name in {"serial", "serial_number"}
            if is_serial_field or normalized_query in display_value.casefold() or (
                source._meta.model_name == "user"
                and name_matches
                and field.name in {"name", "surname"}
            ):
                field_label = "IP Address" if field.name == "ip_address" else field.verbose_name.title()
                match_key = (display_value, field_label)
                if match_key not in seen_matches:
                    field_matches.append(match_key)
                    seen_matches.add(match_key)

    title = str(obj)
    if obj._meta.model_name == "peripheral":
        title = f"{obj.peripheral_type} {obj.device}"

    for display_value, field_label in field_matches:
        title = re.sub(
            re.escape(display_value),
            f"{field_label}: {display_value}",
            title,
            count=1,
            flags=re.IGNORECASE,
        )

    return title[:1].upper() + title[1:]


def generic_record_detail(request, app_label, model_name, pk):
    model_class = apps.get_model(app_label, model_name)
    obj = get_object_or_404(model_class, pk=pk)

    field_data = []
    for field in obj._meta.fields:
        if field.name == "id":
            continue
        value = getattr(obj, field.name, None)
        if value is None:
            display_value = "—"
        elif hasattr(value, "all"):
            display_value = ", ".join(str(item) for item in value.all()) or "—"
        else:
            display_value = str(value)

        field_data.append((field.verbose_name, display_value))

    context = {
        "object": obj,
        "model_name": obj._meta.verbose_name.title(),
        "model_name_slug": obj._meta.model_name,
        "app_label": obj._meta.app_label,
        "field_data": field_data,
    }
    return render(request, "inventory/object-card.html", context)


def global_search_view(request):
    query = request.GET.get('q', '').strip()
    results = []
    search_icons = {
        'city': 'bi-geo-alt',
        'area': 'bi-map',
        'building': 'bi-building',
        'floor': 'bi-layers',
        'commonarea': 'bi-grid',
        'room': 'bi-door-open',
        'space': 'bi-grid-3x3-gap',
        'socket': 'bi-ethernet',
        'generaldirectorate': 'bi-diagram-3',
        'directorate': 'bi-diagram-2',
        'department': 'bi-diagram-3',
        'office': 'bi-briefcase',
        'user': 'bi-people',
        'assignment': 'bi-clipboard-check',
        'desktopcomputer': 'bi-pc-display',
        'allinonecomputer': 'bi-display',
        'laptopcomputer': 'bi-laptop',
        'servercomputer': 'bi-server',
        'printer': 'bi-printer',
        'ups': 'bi-battery-charging',
        'switch': 'bi-hdd-rack',
        'accesspoint': 'bi-router',
        'phone': 'bi-telephone',
        'peripheral': 'bi-usb-symbol',
        'device': 'bi-pc-display',
    }

    if query:
        raw_results = watson.search(query)
        for entry in raw_results:
            obj = entry.object
            model_name_key = getattr(obj._meta, 'model_name', '') if hasattr(obj, '_meta') else ''
            model_name = obj._meta.verbose_name.title() if hasattr(obj, '_meta') else obj.__class__.__name__
            results.append({
                'title': get_search_result_title(obj, query),
                'model_type': model_name,
                'icon': search_icons.get(model_name_key, 'bi-search'),
                'url': get_search_result_url(obj),
            })

    return render(request, 'inventory/search-results.html', {
        'query': query,
        'results': results,
        'page_heading': 'Search results',
        'page_subtitle': f"Results for {query or 'all records'}",
        'page_icon': 'bi bi-search',
        'hide_header_actions': True,
    })