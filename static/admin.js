function fetchList(kindName) {
    $.getJSON('/admin/api/' + kindName + '/entities', function(data) {
        return data;
    }).fail(function (xhr, status, error) {
        return {'status': status, 'error': error}
    })
}

// Ajax loading indicator show/hide
$.ajaxSetup({
    beforeSend:function(){
        $(".ajax-loader-container").show();
    },
    complete:function(){
        $(".ajax-loader-container").hide();
    }
});

$(document).ready(function () {
    // Attack ajax loader to page.
    var ajax_loader_c = $('.ajax-loader-container');
    if (ajax_loader_c)
        ajax_loader_c.append($("<img/>", {
            'src': '/static/ajax-loader.gif',
            'alt': 'Загрузка...'
        }));

    // Getting and building list of entities for a kind.
    if ($('#entities-list-multi')) {
        $("a[data-toggle='tab']").on("shown.bs.tab", function(e) {
            // Verbose kind name must be duplicated in content header.
            var textForHeader = $(this).text().toUpperCase();
            $('#content-header').text(textForHeader);

            var reqKind = $(this).attr('href').slice(1);
            var tabPaneContent = $('#' + reqKind).find('.tab-pane-items');

            $.getJSON('/admin/api/' + reqKind + '/entities', function (data) {
                tabPaneContent.empty();

                // list container
                var listContainer = $(
                    '<div/>', {class: 'list-group'}
                ).appendTo(tabPaneContent);

                // 'add new item' button
                $('<a/>', {
                    href: '/admin/new?kind=' + reqKind,
                    class: 'list-group-item list-group-item-success',
                    text: '+ Создать'
                }).insertBefore(listContainer);

                // iterating data to fill list container
                $.each(data['items'], function (i, item) {
                    var listItem = $('<div/>', {
                        class: 'list-group-item'
                    }).appendTo(listContainer);

                    // item link
                    $('<a/>', {
                        href: '/admin/entity?id=' + item.id,
                        target: '_blank',
                        text: item.value
                    }).appendTo(listItem);

                    // delete link and icon
                    $('<a/>', {
                        href: '/admin/delete?id=' + item.id,
                        target: '_blank',
                        class: 'pull-right',
                        title: 'Удалить'
                    }).append($('<i/>', {
                        class: 'glyphicon glyphicon-remove text-danger'
                    })).appendTo(listItem);
                })
            }).fail(function (xhr, status, error) {
                var msg = jQuery('<div/>', {
                    class: 'alert alert-danger',
                    role: 'alert'
                });
                $('<h4/>', {text: 'Ошибка!'}).appendTo(msg);
                $('<p/>', {
                    'text': 'Во время получения списка произошла ошибка: ' +
                        status + ', ' + error + '.'
                }).appendTo(msg);

                tabPaneContent.empty().append(msg);
            });
        });

        $('#tabs').find('a[href=#Service]').tab('show')
    }
});