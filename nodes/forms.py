from django import forms
from django.db.models import Prefetch, Q
from django.utils import timezone
from .models import *


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL MIXIN FOR ALL DEVICE FORMS
# ─────────────────────────────────────────────────────────────────────────────

class SocketSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        socket = getattr(value, 'instance', None)
        if socket:
            option['attrs']['data-space-id'] = socket.space_id or ''
            option['attrs']['data-common-area-id'] = socket.common_area_id or ''
        return option


class DeviceSocketLabelMixin:
    """
    A mixin applied to forms whose models inherit from the parent Device model.
    It automatically adds the building name next to the socket code in dropdown lists
    without modifying the database or the global Socket.__str__() representation.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'socket' in self.fields:
            socket_field = self.fields['socket']
            socket_field.widget = SocketSelect(attrs=socket_field.widget.attrs.copy())
            self.fields['socket'].queryset = self.fields['socket'].queryset.select_related(
                'building',
                'space__room__floor',
                'common_area__floor',
            )
            self.fields['socket'].label_from_instance = self._socket_label

    @staticmethod
    def _socket_label(socket):
        building_name = socket.building.name if socket.building_id else 'Unknown building'
        if socket.space_id:
            floor = socket.space.room.floor
            location = (
                f"Room {socket.space.room.room_code} - "
                f"Space {socket.space.name}"
            )
        elif socket.common_area_id:
            floor = socket.common_area.floor
            location = (
                f"{socket.common_area.get_area_type_display()} - "
                f"{socket.common_area.name}"
            )
        else:
            floor = None
            location = 'Unknown location'

        floor_label = f"Floor {floor.floor_number}" if floor else 'Unknown floor'
        return f"{socket.socket_code} - {building_name} - {floor_label} - {location}"


# ─────────────────────────────────────────────────────────────────────────────
# ORGANIZATIONAL STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

class GeneralDirectorateForm(forms.ModelForm):
    class Meta:
        model = GeneralDirectorate
        fields = ['name', 'is_active', 'valid_from', 'valid_to']


class DirectorateForm(forms.ModelForm):
    class Meta:
        model = Directorate
        fields = ['name', 'general_directorate', 'is_active', 'valid_from', 'valid_to']


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'directorate', 'is_active', 'valid_from', 'valid_to']


class OfficeForm(forms.ModelForm):
    class Meta:
        model = Office
        fields = ['name', 'department', 'is_active', 'valid_from', 'valid_to']


# ─────────────────────────────────────────────────────────────────────────────
# GEOGRAPHICAL STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ['name']


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ['name', 'city']


class BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = ['name', 'address','postal_code', 'area', 'is_active', 'valid_from', 'valid_to']


class FloorForm(forms.ModelForm):
    class Meta:
        model = Floor
        fields = ['floor_number', 'building', 'is_active', 'valid_from', 'valid_to']


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['room_code', 'floor', 'is_active', 'valid_from', 'valid_to']


class SpaceForm(forms.ModelForm):
    class Meta:
        model = Space
        fields = ['name', 'room', 'is_active', 'valid_from', 'valid_to']


class CommonAreaForm(forms.ModelForm):
    class Meta:
        model = CommonArea
        fields = ['name', 'area_type', 'floor', 'is_active', 'valid_from', 'valid_to']


class SocketForm(forms.ModelForm):
    class Meta:
        model = Socket
        fields = ['socket_code', 'space', 'common_area', 'valid_from', 'valid_to']


# ─────────────────────────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────────────────────────

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'name', 'surname', 'email', 'phone', 'status',
            'general_directorate', 'directorate', 'department', 'office',
            'is_active', 'valid_from', 'valid_to',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone'].label = 'Personal Phone'

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['user', 'device', 'assignment_date', 'end_date', 'assignment_type', 'notes']  


class MaterialHandoverForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(
            assignment__assignment_date__lte=timezone.localdate(),
        ).filter(
            Q(assignment__end_date__isnull=True) | Q(assignment__end_date__gte=timezone.localdate())
        ).select_related(
            'general_directorate', 'directorate', 'department', 'office'
        ).prefetch_related(
            Prefetch(
                'assignment_set',
                queryset=Assignment.objects.filter(
                    assignment_date__lte=timezone.localdate(),
                ).filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate())
                ).select_related('device'),
                to_attr='active_assignments',
            )
        ).order_by('surname', 'name').distinct(),
        label='Users',
        widget=forms.SelectMultiple(attrs={'size': 1}),
    )
    report_date = forms.DateField(
        label='Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    comments = forms.CharField(
        label='Comments',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['users'].label_from_instance = self._user_label
        self.fields['users'].widget.attrs['class'] = 'form-select'
        self.fields['report_date'].widget.attrs['class'] = 'form-control'
        self.fields['comments'].widget.attrs['class'] = 'form-control'

    @staticmethod
    def _user_label(user):
        organization = ' / '.join(
            str(value) for value in (user.general_directorate, user.department) if value
        )
        label = f'{user} - {organization}' if organization else str(user)
        assigned_devices = []
        for assignment in getattr(user, 'active_assignments', []):
            specific_device = assignment.device.get_specific_device()
            device_type = getattr(specific_device, 'device_label', 'Device')
            assignment_type = assignment.get_assignment_type_display()
            assigned_devices.append(
                f'{device_type} - {assignment.device.serial} ({assignment_type})'
            )
        if assigned_devices:
            label += f' - Assigned devices: {", ".join(assigned_devices)}'
        return label

    @staticmethod
    def _device_label(device):
        specific_device = device.get_specific_device()
        device_type = getattr(specific_device, 'device_label', 'Device')
        identity = f'{device_type}: {device.brand} - {device.serial}'
        location = MaterialHandoverForm._device_location(device)
        assignments = getattr(device, 'active_assignments', [])
        assignment_label = '; '.join(
            f'{assignment.user} ({assignment.get_assignment_type_display()})'
            for assignment in assignments
        ) or 'Unassigned'
        return f'{identity} | {location} | Assigned: {assignment_label}'

    @staticmethod
    def _device_location(device):
        building = device.building
        if not building:
            return 'Location unknown'

        location_parts = [
            building.area.city.name,
            building.area.name,
            building.name,
            f'Floor {device.floor.floor_number}',
        ]
        if device.space:
            location_parts.extend([
                f'Room {device.space.room.room_code}',
                device.space.name,
            ])
        elif device.common_area:
            location_parts.append(device.common_area.name)
        return ' / '.join(str(part) for part in location_parts if part)

    def clean(self):
        cleaned_data = super().clean()
        selected_users = list(cleaned_data.get('users') or [])
        if not selected_users:
            raise forms.ValidationError('Select at least one user.')

        shared_device_ids = set()
        for user in selected_users:
            user_device_ids = set(
                Assignment.objects.filter(
                    user=user,
                    assignment_date__lte=timezone.localdate(),
                ).filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate())
                ).values_list('device_id', flat=True)
            )
            if not user_device_ids:
                raise forms.ValidationError(f'{user} does not currently have an assigned device.')
            if not shared_device_ids:
                shared_device_ids = user_device_ids
            else:
                shared_device_ids &= user_device_ids

        if not shared_device_ids:
            raise forms.ValidationError('The selected users must share the same assigned device.')

        selected_devices = list(
            Device.objects.filter(pk__in=shared_device_ids).select_related(
                'space__room__floor__building__area__city',
                'common_area__floor__building__area__city',
            ).prefetch_related(
                Prefetch(
                    'peripherals',
                    queryset=Peripheral.objects.order_by('peripheral_type', 'serial_number'),
                )
            )
        )

        if len(selected_devices) != 1:
            raise forms.ValidationError('The selected users must share the same assigned device.')

        cleaned_data['selected_users'] = selected_users
        cleaned_data['selected_devices'] = selected_devices
        return cleaned_data

class DesktopForm( DeviceSocketLabelMixin, forms.ModelForm):
    class Meta:
        model = DesktopComputer
        fields = [
            'cpu', 'ram_gb', 'storage_gb', 'brand', 'model', 'serial',
            'registration_code', 'ip_address', 'mac_address', 'usage_type','space', 'common_area','socket', 'is_active', 'valid_from', 'valid_to']   

class AllInOneForm( DeviceSocketLabelMixin, forms.ModelForm):
    class Meta:
        model = AllInOneComputer
        fields = [
            'cpu', 'ram_gb', 'storage_gb', 'brand', 'model', 'serial','screen_size',
            'registration_code', 'ip_address', 'mac_address', 'usage_type','space', 'common_area','socket', 'is_active', 'valid_from', 'valid_to']   

class LaptopForm( DeviceSocketLabelMixin, forms.ModelForm):
    class Meta:
        model = LaptopComputer
        fields = [
            'cpu', 'ram_gb', 'storage_gb', 'brand', 'model', 'serial','screen_size',
            'registration_code', 'ip_address', 'mac_address', 'usage_type','space', 'common_area','socket', 'is_active', 'valid_from', 'valid_to']            
        
class ServerForm( DeviceSocketLabelMixin, forms.ModelForm):
    class Meta:
        model = ServerComputer
        fields = [
            'rack_unit', 'brand', 'model', 'serial',
            'registration_code', 'ip_address', 'mac_address', 'usage_type','space', 'common_area','socket', 'is_active', 'valid_from', 'valid_to']   

class PrinterForm( DeviceSocketLabelMixin, forms.ModelForm):
    class Meta:
        model = Printer
        fields = [
            'printer_type', 'brand', 'model', 'serial',
            'registration_code', 'ip_address', 'mac_address', 'usage_type','space', 'common_area','socket', 'is_active', 'valid_from', 'valid_to']        

class UpsForm( DeviceSocketLabelMixin, forms.ModelForm):
    class Meta:
        model = Ups
        fields = [
            'capacity_va', 'brand', 'model', 'serial',
            'registration_code', 'ip_address', 'mac_address', 'usage_type','space', 'common_area','socket', 'is_active', 'valid_from', 'valid_to']        
        
class SwitchForm( DeviceSocketLabelMixin, forms.ModelForm):
    class Meta:
        model = Switch
        fields = [
            'layer_capability', 'total_ports', 'poe_supported', 'poe_budget_watts', 'uplink_speed', 'downlink_speed', 'brand', 'model', 'serial',
            'registration_code', 'ip_address', 'mac_address', 'usage_type','space', 'common_area','socket', 'is_active', 'valid_from', 'valid_to']      

class AccessPointForm( DeviceSocketLabelMixin, forms.ModelForm):
    class Meta:
        model = AccessPoint
        fields = [
            'gps_lat', 'gps_lon', 'brand', 'model', 'serial',
            'registration_code', 'ip_address', 'mac_address', 'usage_type','space', 'common_area','socket', 'is_active', 'valid_from', 'valid_to']
        
class PhoneForm( DeviceSocketLabelMixin, forms.ModelForm):
    class Meta:
        model = Phone
        fields = [
            'phone_type', 'brand', 'model', 'serial',
            'registration_code', 'ip_address', 'mac_address','phone_number','usage_type','space', 'common_area','socket', 'is_active', 'valid_from', 'valid_to']        
        
class PeripheralForm(forms.ModelForm):
    class Meta:
        model = Peripheral
        fields = [
            'device', 'peripheral_type', 'brand', 'model', 'serial_number','specifications',]
