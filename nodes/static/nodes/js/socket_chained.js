'use strict';
document.addEventListener('DOMContentLoaded', function () {
    var socket = document.getElementById('id_socket');
    var space = document.getElementById('id_space');
    var commonArea = document.getElementById('id_common_area');

    if (!socket || !space || !commonArea) return;

    var placeholder = socket.options[0];
    var socketOptions = Array.prototype.slice.call(socket.options, 1);

    function filterSockets() {
        var selectedSocket = socket.value;
        var locationId = space.value || commonArea.value;
        var locationAttribute = space.value ? 'spaceId' : 'commonAreaId';

        socket.replaceChildren(placeholder);
        socketOptions.forEach(function (option) {
            if (!locationId || option.dataset[locationAttribute] === locationId) {
                socket.appendChild(option);
            }
        });
        socket.value = selectedSocket;
    }

    space.addEventListener('change', function () {
        if (space.value) commonArea.value = '';
        filterSockets();
    });
    commonArea.addEventListener('change', function () {
        if (commonArea.value) space.value = '';
        filterSockets();
    });
    filterSockets();
});
