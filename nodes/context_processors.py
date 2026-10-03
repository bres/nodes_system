from django.urls import ResolverMatch, reverse
from .models import City, Area, Building, Floor, CommonArea, Room, Space

PAGE_TITLE_MAP = {
    'dashboard': 'Dashboard',
    'cities-list': 'Cities',
    'areas-list': 'Areas',
    'buildings-list': 'Buildings',
    'floors-list': 'Floors',
    'common-areas-list': 'Common Areas',
    'rooms-list': 'Rooms',
    'spaces-list': 'Spaces',
    'directorates-list': 'Directorates',
    'general-directorates-list': 'General Directorates',
    'departments-list': 'Departments',
    'offices-list': 'Offices',
    'users-list': 'Users',
    'assignments-list': 'Assignments',
    'allInOnes-list': 'All In Ones',
    'laptops-list': 'Laptops',
    'desktops-list': 'Desktops',
    'workstations-list': 'All PCs',
    'sockets-list': 'Sockets',
    'access-points-list': 'Access Points',
    'phones-list': 'Phones',
    'peripherals-list': 'Peripherals',
    'servers-list': 'Servers',
    'printers-list': 'Printers',
    'switches-list': 'Switches',
    'upses-list': 'UPS Units',
    'devices-list': 'Devices',
    'ping-all-devices': 'Ping All Devices',
    'device-statistics': 'Statistics',
    'queries-list': 'Queries',
}

PAGE_ICON_MAP = {
    'dashboard': 'bi bi-grid',
    'cities-list': 'bi bi-geo-alt',
    'areas-list': 'bi bi-map',
    'buildings-list': 'bi bi-building',
    'floors-list': 'bi bi-layers',
    'common-areas-list': 'bi bi-grid',
    'rooms-list': 'bi bi-door-open',
    'spaces-list': 'bi bi-grid-3x3-gap',
    'directorates-list': 'bi bi-diagram-2',
    'general-directorates-list': 'bi bi-diagram-3',
    'departments-list': 'bi bi-diagram-3',
    'offices-list': 'bi bi-briefcase',
    'users-list': 'bi bi-people',
    'assignments-list': 'bi bi-clipboard-check',
    'allInOnes-list': 'bi bi-display',
    'laptops-list': 'bi bi-laptop',
    'desktops-list': 'bi bi-pc-display',
    'workstations-list': 'bi bi-pc-display',
    'sockets-list': 'bi bi-ethernet',
    'access-points-list': 'bi bi-router',
    'phones-list': 'bi bi-telephone',
    'peripherals-list': 'bi bi-usb-symbol',
    'servers-list': 'bi bi-server',
    'printers-list': 'bi bi-printer',
    'switches-list': 'bi bi-hdd-rack',
    'upses-list': 'bi bi-battery-charging',
    'devices-list': 'bi bi-pc-display',
    'ping-all-devices': 'bi bi-broadcast-pin',
    'device-statistics': 'bi bi-bar-chart-line',
    'queries-list': 'bi bi-search',
}

PAGE_ADD_URL_MAP = {
    'general-directorates-list': 'new-general-directorate',
    'directorates-list': 'new-directorate',
    'departments-list': 'new-department',
    'offices-list': 'new-office',
    'cities-list': 'new-city',
    'areas-list': 'new-area',
    'buildings-list': 'new-building',
    'floors-list': 'new-floor',
    'common-areas-list': 'new-common-area',
    'rooms-list': 'new-room',
    'spaces-list': 'new-space',
    'sockets-list': 'new-socket',
    'assignments-list': 'create-assignment',
    'users-list': 'create-user',
    'allInOnes-list': 'new-allInOne',
    'desktops-list': 'new-desktop',
    'laptops-list': 'new-laptop',
    'servers-list': 'new-server',
    'printers-list': 'new-printer',
    'upses-list': 'new-ups',
    'switches-list': 'new-switches',
    'access-points-list': 'new-access-points',
    'phones-list': 'new-phones',
    'peripherals-list': 'new-peripherals',
}

PAGE_EXPORT_MODEL_MAP = {
    'general-directorates-list': 'general-directorate',
    'directorates-list': 'directorate',
    'departments-list': 'department',
    'offices-list': 'office',
    'cities-list': 'city',
    'areas-list': 'area',
    'buildings-list': 'building',
    'floors-list': 'floor',
    'common-areas-list': 'common-area',
    'rooms-list': 'room',
    'spaces-list': 'space',
    'sockets-list': 'socket',
    'assignments-list': 'assignment',
    'users-list': 'user',
    'allInOnes-list': 'allinonecomputer',
    'desktops-list': 'desktopcomputer',
    'workstations-list': 'desktopcomputer',
    'laptops-list': 'laptopcomputer',
    'servers-list': 'servercomputer',
    'printers-list': 'printer',
    'upses-list': 'ups',
    'switches-list': 'switch',
    'access-points-list': 'accesspoint',
    'phones-list': 'phone',
    'peripherals-list': 'peripheral',
    'devices-list': 'device',
}

PAGE_CATEGORY_MAP = {
    **dict.fromkeys([
        'cities-list', 'areas-list', 'buildings-list', 'floors-list',
        'common-areas-list', 'rooms-list', 'spaces-list', 'sockets-list',
        'city-detail', 'area-detail', 'building-detail', 'floor-detail',
        'common-area-detail', 'room-detail', 'space-detail', 'socket-detail',
    ], 'spatial'),
    **dict.fromkeys([
        'general-directorates-list', 'directorates-list', 'departments-list',
        'offices-list', 'users-list', 'assignments-list',
        'general-directorate-detail', 'directorate-detail', 'department-detail',
        'office-detail', 'user-detail', 'assignment-detail',
    ], 'organic'),
    **dict.fromkeys([
        'allInOnes-list', 'desktops-list', 'laptops-list', 'servers-list',
        'printers-list', 'upses-list', 'switches-list', 'access-points-list',
        'phones-list', 'peripherals-list', 'devices-list',
        'allInOne-detail', 'desktop-detail', 'laptop-detail', 'server-detail',
        'printer-detail', 'ups-detail', 'switch-detail', 'access-point-detail',
        'phone-detail', 'peripheral-detail',
    ], 'hardware'),
}

DETAIL_PAGE_MAP = {
    'city-detail': ('Cities', 'bi bi-geo-alt', 'cities-list', 'update-city', 'delete-city'),
    'area-detail': ('Areas', 'bi bi-map', 'areas-list', 'update-area', 'delete-area'),
    'building-detail': ('Buildings', 'bi bi-building', 'buildings-list', 'update-building', 'delete-building'),
    'floor-detail': ('Floors', 'bi bi-layers', 'floors-list', 'update-floor', 'delete-floor'),
    'common-area-detail': ('Common Areas', 'bi bi-grid', 'common-areas-list', 'update-common-area', 'delete-common-area'),
    'room-detail': ('Rooms', 'bi bi-door-open', 'rooms-list', 'update-room', 'delete-room'),
    'space-detail': ('Spaces', 'bi bi-grid-3x3-gap', 'spaces-list', 'update-space', 'delete-space'),
    'socket-detail': ('Sockets', 'bi bi-ethernet', 'sockets-list', 'update-socket', 'delete-socket'),
    'general-directorate-detail': ('General Directorates', 'bi bi-diagram-3', 'general-directorates-list', 'update-general-directorate', 'delete-general-directorate'),
    'directorate-detail': ('Directorates', 'bi bi-diagram-2', 'directorates-list', 'update-directorate', 'delete-directorate'),
    'department-detail': ('Departments', 'bi bi-diagram-3', 'departments-list', 'update-department', 'delete-department'),
    'office-detail': ('Offices', 'bi bi-briefcase', 'offices-list', 'update-office', 'delete-office'),
    'user-detail': ('Users', 'bi bi-people', 'users-list', 'edit-user', 'delete-user'),
    'assignment-detail': ('Assignments', 'bi bi-clipboard-check', 'assignments-list', 'edit-assignment', 'delete-assignment'),
    'desktop-detail': ('Desktops', 'bi bi-pc-display', 'desktops-list', 'update-desktop', 'delete-desktop'),
    'allInOne-detail': ('All In Ones', 'bi bi-display', 'allInOnes-list', 'update-allInOne', 'delete-allInOne'),
    'laptop-detail': ('Laptops', 'bi bi-laptop', 'laptops-list', 'update-laptop', 'delete-laptop'),
    'server-detail': ('Servers', 'bi bi-server', 'servers-list', 'update-server', 'delete-server'),
    'printer-detail': ('Printers', 'bi bi-printer', 'printers-list', 'update-printer', 'delete-printer'),
    'ups-detail': ('UPS Units', 'bi bi-battery-charging', 'upses-list', 'update-ups', 'delete-ups'),
    'switch-detail': ('Switches', 'bi bi-hdd-rack', 'switches-list', 'update-switches', 'delete-switches'),
    'access-point-detail': ('Access Points', 'bi bi-router', 'access-points-list', 'update-access-points', 'delete-access-points'),
    'phone-detail': ('Phones', 'bi bi-telephone', 'phones-list', 'update-phones', 'delete-phones'),
    'peripheral-detail': ('Peripherals', 'bi bi-usb-symbol', 'peripherals-list', 'update-peripherals', 'delete-peripherals'),
}


def page_header(request):
    route_name = getattr(getattr(request, 'resolver_match', None), 'url_name', None)
    detail_config = DETAIL_PAGE_MAP.get(route_name)
    object_pk = getattr(getattr(request, 'resolver_match', None), 'kwargs', {}).get('pk')

    route_is_edit = bool(route_name) and (
        route_name.startswith('update-')
        or route_name.startswith('edit-')
        or route_name.startswith('delete-')
    )
    route_is_create = bool(route_name) and route_name.startswith('new-')

    if detail_config:
        title, icon, list_route, edit_route, delete_route = detail_config
        return {
            'page_title': title,
            'page_icon': icon,
            'page_add_url': '',
            'page_is_detail': True,
            'page_is_edit': False,
            'page_list_url': reverse(list_route),
            'page_edit_url': reverse(edit_route, kwargs={'pk': object_pk}),
            'page_delete_url': reverse(delete_route, kwargs={'pk': object_pk}),
            'page_category': PAGE_CATEGORY_MAP.get(route_name, ''),
            'page_export_model_name': PAGE_EXPORT_MODEL_MAP.get(list_route, ''),
            'page_export_object_pk': object_pk,
            **_location_breadcrumb(request),
        }

    title = PAGE_TITLE_MAP.get(route_name)
    icon = PAGE_ICON_MAP.get(route_name, 'bi bi-list-ul')
    add_url = reverse(PAGE_ADD_URL_MAP[route_name]) if route_name in PAGE_ADD_URL_MAP else ''

    parent_breadcrumb = _location_breadcrumb(request)

    if title is None and route_name:
        title = route_name.replace('-', ' ').replace('_', ' ').title()

    return {
        'page_title': title or '',
        'page_icon': icon,
        'page_add_url': add_url,
        'page_is_edit': route_is_edit or route_is_create,
        'page_category': PAGE_CATEGORY_MAP.get(route_name, ''),
        'page_export_model_name': PAGE_EXPORT_MODEL_MAP.get(route_name, ''),
        'page_is_statistics': route_name == 'device-statistics',
        **parent_breadcrumb,
    }
def _location_breadcrumb(request):
    location_type = request.GET.get('location_type')
    location_id = request.GET.get('location_id')
    location_config = {
        'city': (City, 'city-detail'),
        'area': (Area, 'area-detail'),
        'building': (Building, 'building-detail'),
        'floor': (Floor, 'floor-detail'),
        'common_area': (CommonArea, 'common-area-detail'),
        'room': (Room, 'room-detail'),
        'space': (Space, 'space-detail'),
    }
    model, detail_route = location_config.get(location_type, (None, None))
    if not model or not location_id or not location_id.isdigit():
        return {}

    parent = model.objects.filter(pk=location_id).first()
    if parent is None:
        return {}

    return {
        'parent_breadcrumb_label': str(parent),
        'parent_breadcrumb_url': reverse(detail_route, kwargs={'pk': parent.pk}),
        'location_query': f'location_type={location_type}&location_id={parent.pk}',
    }
