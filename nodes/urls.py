from django.urls import path,include
from . import views
from django.urls import path
from .views import global_search_view


urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('general-directorates/', views.general_directorates_list, name='general-directorates-list'),
    path('general-directorates/<int:pk>/', views.general_directorate_detail, name='general-directorate-detail'),
    path('new-general-directorate/', views.new_general_directorate, name='new-general-directorate'),
    path('update-general-directorate/<int:pk>/', views.update_general_directorate, name='update-general-directorate'),
    path('delete-confirm/<int:pk>/', views.delete_general_directorate, name='delete-general-directorate'),

    path('directorates/', views.directorates_list, name='directorates-list'),
    path('directorates/<int:pk>/', views.directorate_detail, name='directorate-detail'),
    path('new-directorate/', views.new_directorate, name='new-directorate'),
    path('update-directorate/<int:pk>/', views.update_directorate, name='update-directorate'),
    path('delete-directorate/<int:pk>/', views.delete_directorate, name='delete-directorate'),

    path('departments/', views.departments_list, name='departments-list'),
    path('departments/<int:pk>/', views.department_detail, name='department-detail'),
    path('new-department/', views.new_department, name='new-department'),
    path('update-department/<int:pk>/', views.update_department, name='update-department'),
    path('delete-department/<int:pk>/', views.delete_department, name='delete-department'),

    path('offices/', views.offices_list, name='offices-list'),
    path('offices/<int:pk>/', views.office_detail, name='office-detail'),
    path('new-office/', views.new_office, name='new-office'),
    path('update-office/<int:pk>/', views.update_office, name='update-office'),
    path('delete-office/<int:pk>/', views.delete_office, name='delete-office'),

    path('cities/', views.cities_list, name='cities-list'),
    path('cities/<int:pk>/', views.city_detail, name='city-detail'),
    path('new-city/', views.new_city, name='new-city'),
    path('update-city/<int:pk>/', views.update_city, name='update-city'),
    path('delete-city/<int:pk>/', views.delete_city, name='delete-city'),

    path('areas/', views.areas_list, name='areas-list'),
    path('areas/<int:pk>/', views.area_detail, name='area-detail'),
    path('new-area/', views.new_area, name='new-area'),
    path('update-area/<int:pk>/', views.update_area, name='update-area'),
    path('delete-area/<int:pk>/', views.delete_area, name='delete-area'),

    path('buildings/', views.buildings_list, name='buildings-list'),
    path('buildings/<int:pk>/', views.building_detail, name='building-detail'),
    path('new-building/', views.new_building, name='new-building'),
    path('update-building/<int:pk>/', views.update_building, name='update-building'),
    path('delete-building/<int:pk>/', views.delete_building, name='delete-building'),

    path('floors/', views.floors_list, name='floors-list'),
    path('floors/<int:pk>/', views.floor_detail, name='floor-detail'),
    path('new-floor/', views.new_floor, name='new-floor'),
    path('update-floor/<int:pk>/', views.update_floor, name='update-floor'),
    path('delete-floor/<int:pk>/', views.delete_floor, name='delete-floor'),

    path('common-areas/', views.common_areas_list, name='common-areas-list'),
    path('common-areas/<int:pk>/', views.common_area_detail, name='common-area-detail'),
    path('new-common-area/', views.new_common_area, name='new-common-area'),
    path('update-common-area/<int:pk>/', views.update_common_area, name='update-common-area'),
    path('delete-common-area/<int:pk>/', views.delete_common_area   , name='delete-common-area'),

    path('rooms/', views.rooms_list, name='rooms-list'),
    path('rooms/<int:pk>/', views.room_detail, name='room-detail'),
    path('new-room/', views.new_room, name='new-room'),
    path('update-room/<int:pk>/', views.update_room, name='update-room'),
    path('delete-room/<int:pk>/', views.delete_room, name='delete-room'),   

    path('spaces/', views.spaces_list, name='spaces-list'),
    path('spaces/<int:pk>/', views.space_detail, name='space-detail'),
    path('new-space/', views.new_space, name='new-space'),
    path('update-space/<int:pk>/', views.update_space, name='update-space'),
    path('delete-space/<int:pk>/', views.delete_space, name='delete-space'),

    path('sockets/', views.sockets_list, name='sockets-list'),
    path('sockets/<int:pk>/', views.socket_detail, name='socket-detail'),
    path('new-socket/', views.new_socket, name='new-socket'),
    path('update-socket/<int:pk>/', views.update_socket, name='update-socket'),
    path('delete-socket/<int:pk>/', views.delete_socket, name='delete-socket'),

    path('assignments/', views.assignments_list, name='assignments-list'),
    path('assignments/<int:pk>/', views.assignment_detail, name='assignment-detail'),
    path('new-assignment/', views.new_assignment, name='create-assignment'),
    path('update-assignment/<int:pk>/', views.update_assignment, name='edit-assignment'),
    path('delete-assignment/<int:pk>/', views.delete_assignment, name='delete-assignment'),
    path('material-handover/', views.material_handover, name='material-handover'),
    path('device-statistics/', views.device_statistics, name='device-statistics'),

    path('users/', views.users_list, name='users-list'),
    path('users/<int:pk>/', views.user_detail, name='user-detail'),
    path('new-user/', views.new_user, name='create-user'),
    path('update-user/<int:pk>/', views.update_user, name='edit-user'),
    path('delete-user/<int:pk>/', views.delete_user, name='delete-user'),

    path('devices/', views.devices_list, name='devices-list'),
    path('workstations/', views.workstations_list, name='workstations-list'),
    path('phone-book/', views.phone_book, name='phone-book'),
   
    path('device/<int:pk>/', views.device_detail, name='device-detail'),
    path('peripherals/', views.peripherals_list, name='peripherals-list'),
    path('peripherals/<int:pk>/', views.peripheral_detail, name='peripheral-detail'),

    path('desktops/', views.desktops_list, name='desktops-list'),
    path('desktops/<int:pk>/', views.desktop_detail, name='desktop-detail'),
    path('new-desktop/', views.newdesktop, name='new-desktop'),
    path('update-desktop/<int:pk>/', views.updatedesktop, name='update-desktop'),
    path('delete-desktop/<int:pk>/', views.deletedesktop, name='delete-desktop'),
    
    path('allInOnes/', views.allInOnes_list, name='allInOnes-list'),
    path('allInOnes/<int:pk>/', views.allInOne_detail, name='allInOne-detail'),
    path('new-allInOne/', views.newallInOne, name='new-allInOne'),
    path('update-allInOne/<int:pk>/', views.updateallInOne, name='update-allInOne'),
    path('delete-allInOne/<int:pk>/', views.deleteallInOne, name='delete-allInOne'),

    path('laptops/', views.laptops_list, name='laptops-list'),
    path('laptops/<int:pk>/', views.laptop_detail, name='laptop-detail'),
    path('new-laptop/', views.newLaptop, name='new-laptop'),
    path('update-laptop/<int:pk>/', views.updateLaptop, name='update-laptop'),
    path('delete-laptop/<int:pk>/', views.deleteLaptop, name='delete-laptop'),

    path('servers/', views.servers_list, name='servers-list'),
    path('servers/<int:pk>/', views.server_detail, name='server-detail'),
    path('new-server/', views.newServer, name='new-server'),
    path('update-server/<int:pk>/', views.updateServer, name='update-server'),
    path('delete-server/<int:pk>/', views.deleteServer, name='delete-server'),

    path('printers/', views.printers_list, name='printers-list'),
    path('printers/<int:pk>/', views.printer_detail, name='printer-detail'),
    path('new-printer/', views.newPrinter, name='new-printer'),
    path('update-printer/<int:pk>/', views.updatePrinter, name='update-printer'),
    path('delete-printer/<int:pk>/', views.deletePrinter, name='delete-printer'),

    path('upses/', views.upses_list, name='upses-list'),
    path('upses/<int:pk>/', views.ups_detail, name='ups-detail'),
    path('new-ups/', views.newUpses, name='new-ups'),
    path('update-ups/<int:pk>/', views.updateUpses, name='update-ups'),
    path('delete-ups/<int:pk>/', views.deleteUpses, name='delete-ups'),

    path('switches/', views.switches_list, name='switches-list'),
    path('switches/<int:pk>/', views.switch_detail, name='switch-detail'),
    path('new-switch/', views.newSwitches, name='new-switches'),
    path('update-switch/<int:pk>/', views.updateSwitches, name='update-switches'),
    path('delete-switch/<int:pk>/', views.deleteSwitches, name='delete-switches'),


    path('access-points/', views.access_points_list, name='access-points-list'),
    path('access-points/<int:pk>/', views.access_point_detail, name='access-point-detail'),
    path('new-access-point/', views.newAccessPoints, name='new-access-points'),
    path('update-access-point/<int:pk>/', views.updateAccessPoints, name='update-access-points'),
    path('delete-access-point/<int:pk>/', views.deleteAccessPoints, name='delete-access-points'),

    path('phones/', views.phones_list, name='phones-list'),
    path('phones/<int:pk>/', views.phone_detail, name='phone-detail'),
    path('new-phone/', views.newPhones, name='new-phones'),
    path('update-phone/<int:pk>/', views.updatePhones, name='update-phones'),
    path('delete-phone/<int:pk>/', views.deletePhones, name='delete-phones'),

    path('peripherals/', views.peripherals_list, name='peripherals-list'),
    path('new-peripheral/', views.newPeripherals, name='new-peripherals'),
    path('update-peripheral/<int:pk>/', views.updatePeripherals, name='update-peripherals'),
    path('delete-peripheral/<int:pk>/', views.deletePeripherals, name='delete-peripherals'),

    path('queries/', views.queries_list, name='queries-list'),
    path('map/', views.map, name='map'),
    path("ping-device/", views.ping_devices, name="ping_device"),
    path("ping-all-devices/", views.ping_devices, name="ping-all-devices"),

    path('search/', global_search_view, name='global-search'),
    path('record/<str:app_label>/<str:model_name>/<int:pk>/', views.generic_record_detail, name='record-detail'),
    path('export/device-statistics/<str:format_name>/', views.export_device_statistics, name='export-device-statistics'),
    path('export/<str:model_name>/<str:format_name>/', views.export_records, name='export-records'),
    path('export/<str:model_name>/<int:pk>/<str:format_name>/', views.export_records, name='export-record'),

]