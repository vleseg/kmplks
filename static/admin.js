// Ajax loading indicator show/hide
$.ajaxSetup({
    beforeSend:function(){
        $("#loading").appendTo("#ajax_loader_container").show();
    },
    complete:function(){
        $("#loading").hide();
    }
});

$(document).ready(function () {
    // Getting and building list of entities for a kind.
    if (window.location.href.indexOf('/admin/list') > -1) {
        $("a[data-toggle='tab']").on("shown.bs.tab", function(e) {
            var reqKind = $(this).attr('href').slice(1);
            var tabPaneContent = $('#' + reqKind).find('.tab-pane-items');
            $('#list-name-pl').find('small').text($(this).text().toUpperCase());

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
            })
        });

        $('#tabs').find('a[href=#Service]').tab('show')
    }
});