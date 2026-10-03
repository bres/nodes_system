import re

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()

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
    'sockets-list': 'bi bi-ethernet',
    'access-points-list': 'bi bi-router',
    'phones-list': 'bi bi-telephone',
    'peripherals-list': 'bi bi-usb-symbol',
    'servers-list': 'bi bi-server',
    'printers-list': 'bi bi-printer',
    'switches-list': 'bi bi-hdd-rack',
    'upses-list': 'bi bi-battery-charging',
    'devices-list': 'bi bi-pc-display',
    'queries-list': 'bi bi-search',
}

PAGE_TITLE_MAP = {
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
    'desktops-list': 'Desktops',
    'sockets-list': 'Sockets',
    'access-points-list': 'Access Points',
    'phones-list': 'Phones',
    'peripherals-list': 'Peripherals',
    'servers-list': 'Servers',
    'printers-list': 'Printers',
    'switches-list': 'Switches',
    'upses-list': 'UPS Units',
    'devices-list': 'Devices',
    'queries-list': 'Queries',
}


@register.filter
def page_icon(value):
    if not value:
        return 'bi bi-list-ul'
    return PAGE_ICON_MAP.get(value, 'bi bi-list-ul')


@register.filter
def page_title(value):
    if not value:
        return ''
    return PAGE_TITLE_MAP.get(value, value.replace('-', ' ').replace('_', ' ').title())


@register.filter
def highlight_search(value, query):
    text = str(value or '')
    search_term = str(query or '').strip()

    def render_text(segment):
        if not search_term:
            return conditional_escape(segment)

        rendered = []
        last_end = 0
        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        for match in pattern.finditer(segment):
            rendered.append(conditional_escape(segment[last_end:match.start()]))
            rendered.append(
                '<mark class="bg-warning-subtle text-dark rounded-1 px-1">'
                f'{conditional_escape(match.group())}</mark>'
            )
            last_end = match.end()

        rendered.append(conditional_escape(segment[last_end:]))
        return ''.join(rendered)

    highlighted = []
    last_end = 0
    ip_pattern = re.compile(r'IP Address:\s*[^|→]+', re.IGNORECASE)
    for match in ip_pattern.finditer(text):
        highlighted.append(render_text(text[last_end:match.start()]))
        highlighted.append(
            '<span class="fw-semibold">'
            f'{render_text(match.group())}</span>'
        )
        last_end = match.end()

    highlighted.append(render_text(text[last_end:]))
    return mark_safe(''.join(highlighted))


DETAIL_CONTEXT_KEYS = {
    'city-detail': 'city',
    'area-detail': 'area',
    'building-detail': 'building',
    'floor-detail': 'floor',
    'common-area-detail': 'common_area',
    'room-detail': 'room',
    'space-detail': 'space',
    'socket-detail': 'socket',
    'general-directorate-detail': 'general_directorate',
    'directorate-detail': 'directorate',
    'department-detail': 'department',
    'office-detail': 'office',
    'user-detail': 'user',
    'assignment-detail': 'assignment',
    'desktop-detail': 'desktop',
    'allInOne-detail': 'device',
    'laptop-detail': 'device',
    'server-detail': 'device',
    'printer-detail': 'device',
    'ups-detail': 'device',
    'switch-detail': 'device',
    'access-point-detail': 'device',
    'phone-detail': 'device',
    'peripheral-detail': 'peripheral',
}


@register.simple_tag(takes_context=True)
def detail_page_label(context):
    """Return the current detail object's display name for the breadcrumb."""
    request = context.get('request')
    route_name = getattr(getattr(request, 'resolver_match', None), 'url_name', None)
    context_key = DETAIL_CONTEXT_KEYS.get(route_name)
    detail_object = context.get(context_key) if context_key else None
    return str(detail_object) if detail_object is not None else 'Details'
